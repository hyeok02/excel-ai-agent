"""The complete Q&A route preserves the numeric-premise verification boundary."""
import asyncio

import pytest

from app.agent.query.intent_models import QuestionIntent
from app.services.workbook_parsing.models import WorkbookSummary
from tests.test_ambiguity_service import _service
from tests.test_metric_observation_answers import _index, _report
from tests.test_metric_premise_answers import _forecast


@pytest.mark.parametrize("source, question, expected", [
    (_forecast(), "2032년 실제 매출이 72백만 달러가 맞아?", "회계연도 예상 Revenue: 72백만 미국 달러"),
    (_report(), "2024년 9월 30일 종료 분기 Operating Income이 650백만 달러가 맞아?",
     "분기 Operating Income: 180백만 미국 달러"),
])
def test_service_corrects_numeric_premise_without_model_guess_or_green_badge(source, question, expected):
    service = _service(QuestionIntent(False, "cell_lookup"))
    answer = asyncio.run(service.answer(question, WorkbookSummary("fixture.xlsx", 0, []),
                                        _index({"Report": source})))
    assert answer.question == question
    assert expected in answer.answer
    assert answer.status == "limited"
    assert answer.verification.level == "source_checked"
    assert "premise_not_confirmed" in answer.verification.checks
    assert "request_alignment" not in answer.verification.checks


@pytest.mark.parametrize("symbol", ["NYSE:ARC", "NASDAQ:VIO"])
@pytest.mark.parametrize("from_model", [False, True])
def test_original_source_ticker_binding_can_correct_scenario_premise(symbol, from_model):
    source = {**_forecast(), "A1": symbol}
    question = f"Report 시트에서 {symbol.split(':')[1]}의 2032년 실제 Revenue는 72백만 달러가 맞아?"
    service = _service(QuestionIntent(False, "cell_lookup", (), from_model))
    answer = asyncio.run(service.answer(question, WorkbookSummary("fixture.xlsx", 0, []),
                                        _index({"Report": source})))
    assert "요청한 실적 값은 확인하지 못했습니다" in answer.answer
    assert "예상 Revenue: 72백만 미국 달러" in answer.answer
    assert answer.status == "limited" and answer.verification.level == "source_checked"
    assert "premise_not_confirmed" in answer.verification.checks
