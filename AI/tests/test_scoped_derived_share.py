"""Scoped denominators retain all in-population categories and raw lineage."""
import pytest

from app.agent.query.scoped_derived_answers import scoped_derived_trend_answer
from tests.tabular_query_fixtures import table_fixture


def rows():
    return [[date, place, category, value * factor] for place, factor in [("서울", 1), ("부산", 10)]
            for date, values in [("2024-01-31", (20, 80)), ("2024-02-29", (30, 70)),
                                 ("2024-03-31", (25, 75))]
            for category, value in zip(("서비스", "생산"), values)]


def answer(data=None, question="서울 사업장 안에서 부서별 인원 비중 추이", headers=None):
    summary, index = table_fixture([(1, 1, [headers or ["Date", "사업장", "부서", "인원"], *(rows() if data is None else data)])])
    return scoped_derived_trend_answer(question, summary, index)


def test_all_categories_inside_filter_have_scoped_whole_not_unfiltered_total():
    result = answer()
    assert result.status == "answered", result.model_dump()
    assert result.verification.level == "request_checked"
    assert "20% → 25%, 5%p 증가" in result.answer
    assert "80% → 75%, 5%p 감소" in result.answer
    assert "상승 뒤 하락 전환" in result.answer
    evidence = {cell.value for cell in result.evidence}
    assert {20, 80, 30, 70, 25, 75} <= evidence
    assert not ({200, 800, 100} & evidence)


def test_single_category_keeps_scope_filters_on_denominator_but_not_target():
    result = answer(question="서울 사업장만 전체 인원 중 서비스 부서 비중 추이")
    assert result.status == "answered", result.model_dump()
    assert result.verification.level == "request_checked"
    assert "20% → 25%, 5%p 증가" in result.answer
    assert "생산 인원 /" not in result.answer


def test_source_schema_not_fixed_department_names():
    data = [[date, "North" if place == "서울" else "South",
             "Orchid" if category == "서비스" else "Pine", value] for date, place, category, value in rows()]
    result = answer(data, "North Site Headcount share trend by Team", ["Date", "Site", "Team", "Headcount"])
    assert result.status == "answered", result.model_dump()
    assert "Orchid" in result.answer and "Pine" in result.answer
    assert "5%p 증가" in result.answer


@pytest.mark.parametrize("modify", [
    lambda data: data[1:],
    lambda data: data + [data[0]],
    lambda data: [[date, place, category, 0] for date, place, category, value in data],
    lambda data: [[date, place, category, None if number == 1 else value]
                  for number, (date, place, category, value) in enumerate(data)],
    lambda data: data + [[date, "서울", "합계", 100] for date in ("2024-01-31", "2024-02-29", "2024-03-31")],
])
def test_bad_complete_grid_cannot_be_green(modify):
    result = answer(modify(rows()))
    assert result and result.status == "insufficient_evidence", result
    assert result.verification.level != "request_checked"


def test_original_simple_share_remains_on_existing_adapter():
    assert answer(question="전체 인원 중 서비스 부서 비중 추이") is None


@pytest.mark.parametrize("question", [
    "서울 사업장만 부서별 인원 비중 추이 퇴사자 제외",
    "서울 사업장만 서비스 부서 인원 비중 추이",
    "서울 사업장만 전체 인원 중 서비스 부서 비중 추이 예측",
    "서울 사업장만 서비스 부서별 인원 비중 추이",
    "서울 사업장만 부서별 인원 전년 동기 대비 비중 추이",
])
def test_unknown_or_ambiguous_denominator_never_verified(question):
    result = answer(question=question)
    assert result and result.status == "insufficient_evidence", result
