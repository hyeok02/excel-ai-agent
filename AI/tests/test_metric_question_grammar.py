"""Polite grammar is not an extra metric, but qualifiers must survive."""
import pytest

from app.agent.query.metric_observation_answers import metric_observation_answer
from app.agent.query.metric_request_coverage import uncovered_request_tokens
from tests.test_metric_observation_answers import _index, _report


@pytest.mark.parametrize("ending", ["얼마야", "얼마인가요", "얼마입니까", "얼마인지 알려줘",
                                  "무엇입니까", "얼마일까요"])
def test_polite_metric_lookup_has_the_same_source_bound_answer(ending):
    answer = metric_observation_answer(
        f"Results 시트에서 2024년 9월 30일 종료 분기 Operating Income은 {ending}?",
        None, _index({"Results": _report()}),
    )
    assert answer.status == "answered"
    assert "180백만 미국 달러" in answer.answer
    assert answer.verification.level == "request_checked"


@pytest.mark.parametrize("qualifier", ["독일", "세후", "유로로", "평균", "중앙값", "10명 이상"])
def test_unknown_qualifiers_are_not_consumed_as_question_grammar(qualifier):
    assert uncovered_request_tokens(f"{qualifier} 얼마입니까?", [], set())
