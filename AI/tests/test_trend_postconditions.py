"""Computed-result selectors cannot be mistaken for harmless question prose."""
import pytest

from app.agent.query.trend_answers import trend_answer
from app.agent.query.trend_postconditions import trend_postcondition_error
from tests.tabular_query_fixtures import table_fixture


def ask(question, headers=None, rows=None):
    headers = headers or ["Date", "사업장", "부서", "인원"]
    rows = rows or [[date, "서울", group, value] for date, first, second in
                   [("2024-01-31", 20, 80), ("2024-02-29", 30, 70), ("2024-03-31", 40, 60)]
                   for group, value in (("A", first), ("B", second))]
    summary, index = table_fixture([(1, 1, [headers, *rows])])
    return trend_answer(question, summary, index)


@pytest.mark.parametrize("suffix", [
    "증가하는 부서만", "감소한 부서만", "상승한 부서는 제외", "하락하는 부서만 보여줘",
    "반등한 부서만", "증가하지 않은 부서만", "증가한 그룹은 빼고", "증감률 상위 1개만",
    "비중 내림차순으로 정렬", "top 1", "only increasing departments", "decreasing departments only",
])
@pytest.mark.parametrize("question", [
    "서울 사업장만 부서별 인원 추이", "서울 사업장만 부서별 인원 증감률 추이",
    "서울 사업장만 부서별 인원 비중 추이",
])
def test_result_filters_or_rankings_are_not_silently_dropped(question, suffix):
    result = ask(question + " " + suffix)
    assert result is not None and result.status == "insufficient_evidence", result
    assert result.verification.level != "request_checked", result.model_dump()


@pytest.mark.parametrize("question", ["인원 추이 증가했어?", "인원 추이 감소했어?", "인원 반등 추이"])
def test_normal_direction_question_is_still_answered(question):
    result = ask(question, ["Date", "인원"], [["2024-01-31", 100], ["2024-02-29", 80], ["2024-03-31", 120]])
    assert result.status == "answered", result.model_dump()
    assert "반등" in result.answer


@pytest.mark.parametrize("label", ["상위 인원", "인원 순위", "증가하는 부서만", "Top 1 Headcount"])
def test_actual_metric_label_is_not_a_result_selector(label):
    result = ask(f"{label} 추이", ["Date", label], [["2024-01-31", 100], ["2024-02-29", 120]])
    assert result.status in {"answered", "limited"}, result.model_dump()
    assert "처리는 아직" not in result.answer


@pytest.mark.parametrize("category", ["증가하는 부서만", "상위", "내림차순", "only increasing"])
def test_literal_category_is_not_misread_as_a_postfilter(category):
    result = ask(f'"{category}" 부서 인원 추이', ["Date", "부서", "인원"],
                 [["2024-01-31", category, 100], ["2024-02-29", category, 120]])
    assert result.status == "answered", result.model_dump()


@pytest.mark.parametrize("question", [
    "인원 추이 증가했는지만 알려줘", "인원 추이 감소했는지만 알려줘", "인원 추이 반등했는지만 알려줘",
    "only explain whether Headcount is increasing", "only tell me whether Headcount is decreasing",
])
def test_whether_question_is_not_a_subset_selector(question):
    assert trend_postcondition_error(question, ()) is None


@pytest.mark.parametrize("direction", ["증가", "감소"])
def test_supported_whether_only_question_stays_answered(direction):
    result = ask(f"인원 추이 {direction}했는지만 알려줘", ["Date", "인원"],
                 [["2024-01-31", 100], ["2024-02-29", 80], ["2024-03-31", 120]])
    assert result.status == "answered", result.model_dump()
