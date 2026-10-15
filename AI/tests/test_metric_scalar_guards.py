"""Scope and scalar regressions using synthetic workbook indexes."""
from datetime import datetime
import pytest
from app.agent.query.metric_observation_answers import metric_observation_answer
from app.agent.query.metric_observation_periods import requested_periods
from app.agent.query.metric_scalar_answers import metric_scalar_answer
from app.agent.query.models import QuestionAnswerStatus
from app.agent.query.question_dates import question_date_bounds
from tests.test_metric_observation_answers import _index, _report

def test_source_metric_specificity_does_not_alias_total_debt_to_all_liabilities():
    source = {
        "A2": "Currency", "A3": "USD", "C2": "Magnitude", "C3": "Millions",
        "B8": "+ Total Debt", "E8": 80, "B12": "LIABILITIES", "E12": 999,
    }
    answer = metric_scalar_answer("총부채(Total Debt)는 얼마야?", None, _index({"Arbitrary": source}))
    assert answer.status is QuestionAnswerStatus.ANSWERED
    assert "80백만 미국 달러" in answer.answer and "999" not in answer.answer
    assert "E8" in {item.reference for item in answer.evidence}


def test_scalar_disagreement_is_not_resolved_by_first_sheet_order():
    one = {"A1": "Currency", "A2": "EUR", "A5": "Cash", "B5": 40}
    two = {"A1": "Currency", "A2": "EUR", "A5": "Cash", "B5": 41}
    index = _index({"One": one, "Two": two})
    answer = metric_scalar_answer("Cash는 얼마야?", None, index)
    assert answer.status is QuestionAnswerStatus.INSUFFICIENT_EVIDENCE
    scoped = metric_scalar_answer("Two 시트의 Cash는 얼마야?", None, index)
    assert scoped.status is QuestionAnswerStatus.ANSWERED
    assert "41유로" in scoped.answer


def test_adjacent_record_value_uses_its_header_not_the_other_side_by_side_table():
    source = {
        "B10": "Region", "C10": "Total Employees", "F10": "Date", "G10": "Total Employees",
        "B11": "East Coast", "C11": 32, "F11": "2031-06-01", "G11": 980,
    }
    answer = metric_scalar_answer("East Coast의 직원 수는?", None, _index({"Operations": source}))
    assert answer.status is QuestionAnswerStatus.ANSWERED
    assert "32명" in answer.answer and "980" not in answer.answer
    assert {"B11", "C10", "C11"} <= {item.reference for item in answer.evidence}


@pytest.mark.parametrize("question", [
    "UnknownCorp의 Operating Income을 2023년과 2024년 비교해줘",
    "Compare UnknownCorp Operating Income in 2023 and 2024",
])
def test_an_unknown_requested_entity_never_gets_another_companys_answer(question):
    answer = metric_observation_answer(question, None, _index({"Results": _report()}))
    assert answer.status is QuestionAnswerStatus.INSUFFICIENT_EVIDENCE


def test_missing_requested_year_does_not_fall_back_to_available_endpoints():
    answer = metric_observation_answer("Operating Income은 2020년에서 2024년 얼마나 변했어?",
                                      None, _index({"Results": _report()}))
    assert answer.status is QuestionAnswerStatus.INSUFFICIENT_EVIDENCE


def test_partial_index_cannot_certify_a_latest_or_unique_value():
    answer = metric_observation_answer("Operating Income은 2023년에서 2024년 얼마나 변했어?",
                                      None, _index({"Results": _report()}, truncated=True))
    assert answer.status is QuestionAnswerStatus.INSUFFICIENT_EVIDENCE


def test_amount_and_growth_rows_with_the_same_label_remain_separate():
    source = _report()
    source.update({"B11": "Annual Growth", "B12": "Operating Income", "C12": 3, "D12": 5, "E12": 6})
    answer = metric_observation_answer("Operating Income은 2023년에서 2024년 얼마나 변했어?",
                                      None, _index({"Results": source}))
    assert answer.status is QuestionAnswerStatus.ANSWERED
    assert not ({"C12", "D12", "E12"} & {item.reference for item in answer.evidence})


@pytest.mark.parametrize("question", [
    "Operating Income은 2023년과 2024년 미국만 비교해줘 조건은 Region=USA야",
    "Compare Operating Income in 2023 and 2024 only where Region is USA",
])
def test_additional_filters_are_not_silently_dropped(question):
    assert metric_observation_answer(question, None, _index({"Results": _report()})) is None


def test_question_dates_accept_plain_and_fiscal_years():
    assert question_date_bounds("Revenue from FY2023 to FY2024") == (
        datetime(2023, 1, 1), datetime(2024, 12, 31),
    )
    assert len(requested_periods("2023 실제와 2024 예상 매출 비교")) == 2


def test_scenario_qualifiers_bind_before_or_after_their_own_year():
    for question in (
        "Compare actual 2025 Revenue to forecast 2026 Revenue",
        "Compare 2025 actual Revenue to 2026 forecast Revenue",
        "2025년 실제 매출과 2026년 예상 매출을 비교해줘",
    ):
        periods = requested_periods(question)
        assert [(item.year, item.scenario) for item in periods] == [(2025, "actual"), (2026, "estimate")]


def test_mixed_unit_periods_are_not_subtracted():
    index = _index({"Results": _report()}, {("Results", "D9"): '"$"#,##0', ("Results", "E9"): '"€"#,##0'})
    answer = metric_observation_answer("Operating Income은 2023년에서 2024년 얼마나 변했어?", None, index)
    assert answer.status is QuestionAnswerStatus.INSUFFICIENT_EVIDENCE
