"""Confirmation wording cannot certify a mismatched source period or scenario."""
import pytest

from app.agent.query.metric_observation_answers import metric_observation_answer
from app.agent.query.models import QuestionAnswerStatus, QuestionVerificationLevel
from tests.test_metric_observation_answers import _index, _report


def _forecast():
    return {
        "B2": "Amounts in USD millions", "B5": "Fiscal Year Ended",
        "C6": "Actuals", "D6": "Estimates", "B7": "Period Ended",
        "C7": "2031-12-31", "D7": "2032-12-31", "B9": "Revenue",
        "C9": 60, "D9": 72,
    }


def _assert_limited(answer):
    assert answer.status is QuestionAnswerStatus.LIMITED
    assert answer.verification.level is QuestionVerificationLevel.SOURCE_CHECKED
    assert "premise_not_confirmed" in answer.verification.checks
    assert answer.confidence <= 0.8


@pytest.mark.parametrize("ending", ["라는 거지?", "가 맞아?", "가 맞지?", "는 맞나요?"])
def test_actual_premise_is_corrected_to_explicit_estimate_not_confirmed(ending):
    question = "2032년 실제 매출이 72백만 달러" + ending
    answer = metric_observation_answer(question, None, _index({"Plan": _forecast()}))
    _assert_limited(answer)
    assert answer.question == question
    assert "요청한 실적 값은 확인하지 못했습니다" in answer.answer
    assert "원본이 명시한 예상 값" in answer.answer
    assert "72백만 미국 달러" in answer.answer
    assert {"D6", "D7", "D9"} <= {item.reference for item in answer.evidence}


@pytest.mark.parametrize("ending", ["맞지?", "가 맞아?"])
def test_wrong_annual_number_for_quarter_returns_only_quarter_amount(ending):
    answer = metric_observation_answer(
        "2024년 9월 30일 종료 분기 Operating Income이 650백만 달러 " + ending,
        None, _index({"Report": _report()}),
    )
    _assert_limited(answer)
    assert "분기 Operating Income: 180백만 미국 달러" in answer.answer
    assert "650" not in answer.answer
    refs = {item.reference for item in answer.evidence}
    assert "F9" in refs and "E9" not in refs


def test_an_asserted_amount_cannot_select_a_scenario_by_value():
    answer = metric_observation_answer(
        "2032년 실제 Revenue가 999백만 달러 맞지?", None, _index({"Plan": _forecast()}),
    )
    _assert_limited(answer)
    assert "72백만 미국 달러" in answer.answer and "999" not in answer.answer


@pytest.mark.parametrize("question", [
    "2030년 실제 Revenue가 72백만 달러 맞지?",
    "다른 회사의 2032년 실제 Revenue가 72백만 달러 맞지?",
    "2032년 실제 Revenue가 72백만 달러이니까 성장 원인은 신사업 맞지?",
    "2032년 실제 Revenue 중 국내만 72백만 달러 맞지?",
])
def test_missing_target_date_or_added_conditions_cannot_be_rewritten(question):
    answer = metric_observation_answer(question, None, _index({"Plan": _forecast()}))
    assert answer is None or "premise_not_confirmed" not in answer.verification.checks


def test_ambiguous_same_period_estimates_remain_unverified():
    one, two = _forecast(), _forecast()
    two["D9"] = 90
    answer = metric_observation_answer(
        "2032년 실제 Revenue가 72백만 달러 맞지?", None, _index({"One": one, "Two": two}),
    )
    assert answer.verification.level is QuestionVerificationLevel.UNVERIFIED


def test_truncated_source_and_missing_formula_cache_are_not_corrected():
    for index in [_index({"Plan": _forecast()}, truncated=True),
                  _index({"Plan": {**_forecast(), "D9": None}})]:
        answer = metric_observation_answer("2032년 실제 Revenue가 72백만 달러 맞지?", None, index)
        assert answer is None or answer.verification.level is QuestionVerificationLevel.UNVERIFIED


def test_regular_metric_lookup_keeps_request_checked_status():
    answer = metric_observation_answer(
        "2032년 예상 Revenue는 얼마야?", None, _index({"Plan": _forecast()}),
    )
    assert answer.status is QuestionAnswerStatus.ANSWERED
    assert answer.verification.level is QuestionVerificationLevel.REQUEST_CHECKED


def test_different_asserted_currency_is_not_certified_or_silently_converted():
    answer = metric_observation_answer(
        "2032년 예상 Revenue가 72천 유로가 맞아?", None, _index({"Plan": _forecast()}),
    )
    _assert_limited(answer)
    assert "72백만 미국 달러" in answer.answer
    assert "72천 유로" not in answer.answer
    assert "그대로 확인한 답변은 아닙니다" in answer.answer


def test_conflicting_actual_values_do_not_authorize_switch_to_unique_estimate():
    one, two = _forecast(), _forecast()
    one.update({"C7": "2032-12-31", "C9": 50})
    two.update({"C7": "2032-12-31", "C9": 80})
    answer = metric_observation_answer(
        "2032년 실제 Revenue가 72백만 달러 맞지?", None, _index({"One": one, "Two": two}),
    )
    assert answer.verification.level is QuestionVerificationLevel.UNVERIFIED
    assert "72백만" not in answer.answer


@pytest.mark.parametrize("original_entity_exists", [False, True])
@pytest.mark.parametrize("owner", ["Actual Holdings의", "Actual Holdings"])
def test_scenario_correction_never_rewrites_an_entity_named_actual(original_entity_exists, owner):
    one, two = _forecast(), _forecast()
    one["A1"], two["A1"], two["D9"] = "Actual Holdings", "예상 Holdings", 99
    sheets = {"One": one, "Two": two} if original_entity_exists else {"Two": two}
    answer = metric_observation_answer(
        owner + " 2032년 실제 Revenue가 72백만 달러 맞지?", None,
        _index(sheets),
    )
    assert answer.verification.level is QuestionVerificationLevel.UNVERIFIED
    assert "99" not in answer.answer


def test_scenario_correction_never_rewrites_an_explicit_sheet_name():
    one, two = _forecast(), _forecast()
    two["D9"] = 99
    answer = metric_observation_answer(
        "2032년 Actual Report 시트 Revenue가 72백만 달러 맞지?", None,
        _index({"Actual Report": one, "예상 Report": two}),
    )
    assert answer.verification.level is QuestionVerificationLevel.UNVERIFIED
    assert "99" not in answer.answer
