"""The common deterministic entry wins over an unrelated aggregate plan."""
import pytest

from tests.support.large_workbook_fixtures import offline
from tests.support.trend_adversarial_fixtures import direct, wrong_aggregation
from tests.tabular_query_fixtures import table_fixture


def _source():
    return table_fixture([(1, 1, [["Date", "Total Employees", "Temporary Employees"],
        ["2023-01-31", 100, 20], ["2023-02-28", 200, 40], ["2023-03-31", 100, 10],
        ["2024-01-31", 150, 30], ["2024-02-29", 240, 24], ["2024-03-31", 130, 39]])])


@pytest.mark.parametrize("question", [
    "Total Employees 증감률 추이를 설명해줘",
    "2024년 Total Employees 전년 동기 대비 증감률 추이를 설명해줘",
    "2024년 Total Employees 전년 동기 대비 증가율이 어떻게 변했어?",
    "Total Employees 중 Temporary Employees의 비중은 늘었어?",
    "2024년 1분기 Total Employees 중 Temporary Employees 비중 추이를 설명해줘",
])
def test_source_bound_derived_answer_survives_wrong_planned_aggregation(question):
    summary, index = _source()
    answer = wrong_aggregation(summary, index, question)
    assert answer.status == "answered", answer.model_dump()
    assert answer.verification.level == "request_checked"
    assert "derived_trend" in answer.selected_tools
    assert "계산식:" in answer.answer and "전체 시작·끝" in answer.answer


@pytest.mark.parametrize("question", [
    "Total Employees와 Temporary Employees 비율 추이를 설명해줘",
    "Total Employees 중 Temporary Employees의 비중 추이를 설명해줘 서울만",
    "2024년 Total Employees 전년 동기 대비 전월 대비 증감률 추이를 설명해줘",
])
def test_uncertain_derived_requests_do_not_fall_through_to_wrong_aggregation(question):
    summary, index = _source()
    answer = wrong_aggregation(summary, index, question)
    assert answer.status == "insufficient_evidence", answer.model_dump()
    assert answer.verification.level == "unverified"


def test_question_without_trend_keyword_still_recognizes_share_movement():
    summary, index = _source()
    answer = direct(summary, index, "Total Employees 중 Temporary Employees의 비중은 늘었어?")
    assert answer.status == "answered", answer.model_dump()
    assert "20% → 30%, 10%p 증가" in answer.answer
