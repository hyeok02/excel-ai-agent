"""Endpoint amounts+rates are not intercepted by derived trajectory routing."""
import asyncio
from datetime import datetime

import pytest

from app.agent import create_default_tool_registry
from app.agent.query.service import WorkbookQuestionService
from app.agent.query.trend_date_bounds import parse_trend_date_bounds
from app.services.workbook_parsing.models import WorkbookSummary
from tests.support.large_workbook_fixtures import offline, NoGeneratedAnswer
from tests.support.trend_fixtures import observations
from tests.test_metric_observation_answers import _index, _report


@pytest.mark.parametrize("phrase", ["2023년에서 2024년으로", "2023년부터 2024년까지", "from 2023 to 2024"])
def test_endpoint_question_returns_both_source_amounts_and_correct_rate(phrase):
    summary = WorkbookSummary("synthetic.xlsx", 0, [])
    index = _index({"Results": _report()})
    question = f"Operating Income은 {phrase} 얼마나 증가했어? 금액과 증가율을 알려줘."
    result = asyncio.run(WorkbookQuestionService(NoGeneratedAnswer(), create_default_tool_registry()).answer(
        question, summary, index))
    assert result.status == "answered", result.model_dump()
    assert result.verification.level == "request_checked"
    assert "520백만 미국 달러" in result.answer and "650백만 미국 달러" in result.answer
    assert "130백만 미국 달러" in result.answer and "25.0000%" in result.answer
    assert "bind_metric_observations" in result.selected_tools


def test_korean_directional_date_particles_keep_trend_boundaries():
    points = observations([10, 15, 30], dates=["2023-01-01", "2024-01-01", "2025-01-01"])
    bounds, error = parse_trend_date_bounds("Metric 추이 2023년에서 2024년으로", points)
    assert error is None
    assert (bounds.start, bounds.end) == (datetime(2023, 1, 1), datetime(2024, 12, 31))


def test_reversed_directional_dates_remain_rejected():
    points = observations([10, 15], dates=["2023-01-01", "2024-01-01"])
    bounds, error = parse_trend_date_bounds("Metric 추이 2024년에서 2023년으로", points)
    assert bounds is None and error
