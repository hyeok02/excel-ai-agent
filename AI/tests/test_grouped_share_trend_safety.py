"""A share certificate must prove the whole original population and units."""
from dataclasses import replace

import pytest

from app.agent.query.grouped_share_trend_answers import grouped_share_trend_answer
from tests.support.trend_scoped_fixtures import formats
from tests.tabular_query_fixtures import table_fixture
from tests.test_grouped_share_trend import ROWS, QUESTION, answer


def fixture():
    return table_fixture([(1, 1, [["Date", "부서", "인원"], *ROWS])])


def unsafe(result):
    assert result is not None
    assert result.status == "insufficient_evidence", result.model_dump()
    assert result.verification.level != "request_checked"


@pytest.mark.parametrize("format_map", [
    {"C3": "0.00%"},
    {f"C{number}": "0.00%" for number in range(2, 8)},
    {"C3": '"USD"0'},
])
def test_mixed_or_non_additive_percent_units_cannot_form_population_total(format_map):
    summary, index = fixture()
    index = formats(summary, index, format_map)
    unsafe(grouped_share_trend_answer(QUESTION, summary, index))


def test_hidden_and_truncated_source_cannot_prove_denominator():
    summary, index = fixture()
    summary.sheets[0].regions[0].hidden_rows.append(3)
    unsafe(grouped_share_trend_answer(QUESTION, summary, index))
    summary, index = fixture()
    index = replace(index, rows=index.rows[:-1], truncated=True,
                    truncated_sheet_names=frozenset({"Arbitrary"}))
    unsafe(grouped_share_trend_answer(QUESTION, summary, index))


@pytest.mark.parametrize("dimension,first,second", [
    ("Scenario", "Actual", "Forecast"), ("Currency", "USD", "EUR"),
    ("회사 코드", 10, 20), ("사업장", "서울", "부산"),
])
def test_population_cannot_combine_unbound_identity_dimensions(dimension, first, second):
    rows = [[date, category, value, first if category == "서비스" else second] for date, category, value in ROWS]
    unsafe(answer(rows, headers=("Date", "부서", "인원", dimension)))


def test_known_extra_filter_is_not_reapplied_only_to_denominator_or_numerator():
    rows = [[date, category, value, "서울"] for date, category, value in ROWS]
    unsafe(answer(rows, "서울 사업장만 전체 인원 중 서비스 부서 비중 추이", ("Date", "부서", "인원", "사업장")))


@pytest.mark.parametrize("question", [
    "전체 인원 중 서비스 부서 비중 추이 2024년 1월 또는 3월",
    "전체 인원 중 서비스 부서 비중 추이 Q1",
    "전체 인원 중 서비스 부서 비중 추이 FY2024 Q1",
    "전체 인원 중 서비스 부서 비중 추이 유로로 환산",
])
def test_unknown_period_or_conversion_is_not_hidden_by_share_grammar(question):
    unsafe(answer(question=question))


def test_all_original_operands_are_cited_at_their_real_values():
    result = answer()
    original = {f"{column}{row}": value for row, values in enumerate([["Date", "부서", "인원"], *ROWS], 1)
                for column, value in zip("ABC", values)}
    assert all(original[cell.reference] == cell.value for cell in result.evidence)
    assert {f"C{number}" for number in range(2, 8)} <= {cell.reference for cell in result.evidence}


def test_non_additive_source_ratio_is_not_summed_into_a_total():
    unsafe(answer(question="전체 Market Share 중 서비스 부서 비중 추이", headers=("Date", "부서", "Market Share")))
