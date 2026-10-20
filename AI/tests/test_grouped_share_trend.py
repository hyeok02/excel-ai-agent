"""Generic categorical shares preserve every denominator operand and period."""
import pytest

from app.agent.query.grouped_share_trend_answers import grouped_share_trend_answer
from tests.tabular_query_fixtures import table_fixture

QUESTION = "전체 인원 중 서비스 부서 비중은 늘었어?"
ROWS = [
    ["2024-01-31", "서비스", 20], ["2024-01-31", "생산", 80],
    ["2024-02-29", "서비스", 30], ["2024-02-29", "생산", 70],
    ["2024-03-31", "서비스", 25], ["2024-03-31", "생산", 75],
]


def answer(rows=None, question=QUESTION, headers=("Date", "부서", "인원")):
    summary, index = table_fixture([(1, 1, [list(headers), *(ROWS if rows is None else rows)])])
    return grouped_share_trend_answer(question, summary, index)


def test_actual_category_share_question_uses_all_categories_and_shows_reversal():
    result = answer()
    assert result.status == "answered", result.model_dump()
    assert result.verification.level == "request_checked"
    assert "20% → 25%, 5%p 증가" in result.answer
    assert "2024-02-29: 30%" in result.answer
    assert "상승 뒤 하락 전환" in result.answer
    assert "2개 범주" in result.answer
    numeric = {item.value for item in result.evidence if isinstance(item.value, (int, float))}
    assert {20, 80, 30, 70, 25, 75} <= numeric
    assert 100 not in numeric  # Computed totals never masquerade as raw cells.


def test_generic_source_bound_names_not_a_service_department_rule():
    rows = [[date, "Orchid" if category == "서비스" else "Pine", value] for date, category, value in ROWS]
    result = answer(rows, "Orchid Team Headcount share of total Headcount trend", ("Date", "Team", "Headcount"))
    assert result.status == "answered", result.model_dump()
    assert "5%p 증가" in result.answer


@pytest.mark.parametrize("change", [
    lambda rows: rows[:-1],
    lambda rows: rows + [rows[0]],
    lambda rows: rows + [["2024-01-31", "합계", 100], ["2024-02-29", "합계", 100], ["2024-03-31", "합계", 100]],
    lambda rows: [[date, category, -1 if number == 2 else value] for number, (date, category, value) in enumerate(rows)],
    lambda rows: [[date, category, 0] for date, category, value in rows],
    lambda rows: [[date, category, None if number == 1 else value] for number, (date, category, value) in enumerate(rows)],
    lambda rows: [[None if number == 1 else date, category, value] for number, (date, category, value) in enumerate(rows)],
])
def test_unproven_or_duplicate_denominator_never_receives_verified_badge(change):
    result = answer(change([row[:] for row in ROWS]))
    assert result is not None
    assert result.status == "insufficient_evidence", result.model_dump()
    assert result.verification.level != "request_checked"


def test_other_company_context_cannot_mix_across_categories():
    rows = [[date, category, value, "A" if category == "서비스" else "B"] for date, category, value in ROWS]
    result = answer(rows, headers=("Date", "부서", "인원", "Company"))
    assert result.status == "insufficient_evidence", result.model_dump()


@pytest.mark.parametrize("question", [
    "서비스 부서 인원 비중 추이", "전체 인원 중 서비스 부서 비중 추이 퇴사자 제외",
    "전체 인원 중 서비스 부서 비중 추이 인원 25 이상", "전체 인원 중 서비스와 생산 부서 비중 추이",
])
def test_unknown_scope_or_unspecified_whole_is_not_dropped(question):
    result = answer(question=question)
    assert result is not None and result.status == "insufficient_evidence", result


def test_quarter_scope_validates_every_in_window_category():
    rows = [*ROWS, ["2023-12-31", "서비스", None], ["2023-12-31", "생산", None]]
    result = answer(rows, question="2024년 1분기 전체 인원 중 서비스 부서 비중 추이")
    assert result.status == "answered", result.model_dump()
    assert "2023-12-31" not in result.answer


def test_metric_name_containing_share_is_not_a_share_operation():
    assert answer(question="전체 Market Share 중 서비스 부서 추이", headers=("Date", "부서", "Market Share")) is None
