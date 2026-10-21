"""Adversarial units, scopes and literal/source semantics for composite rates."""
import pytest

from app.agent.query.scoped_derived_answers import scoped_derived_trend_answer
from tests.tabular_query_fixtures import table_fixture


def ask(matrix, question):
    summary, index = table_fixture([(1, 1, matrix)])
    return scoped_derived_trend_answer(question, summary, index)


def test_group_shares_keep_text_and_boolean_category_types_distinct():
    matrix = [["Date", "범주", "인원", "사업장"],
              *[[date, category, value, "서울"] for date in ("2024-01-31", "2024-02-29")
                for category, value in ((True, 20), (1, 80))]]
    result = ask(matrix, "서울 사업장만 범주별 인원 비중 추이")
    assert result.status == "insufficient_evidence", result.model_dump()


@pytest.mark.parametrize("field,values", [("Currency", ("USD", "EUR")), ("Scenario", ("Actual", "Forecast"))])
def test_cross_group_unit_or_scenario_share_not_verified(field, values):
    matrix = [["Date", "범주", "인원", "사업장", field],
              *[[date, category, amount, "서울", marker] for date in ("2024-01-31", "2024-02-29")
                for category, amount, marker in (("A", 20, values[0]), ("B", 80, values[1]))]]
    if field == "Currency":
        matrix[0][2] = "매출"
    result = ask(matrix, f"서울 사업장만 범주별 {matrix[0][2]} 비중 추이")
    assert result.status == "insufficient_evidence", result.model_dump()


def test_metric_label_with_operator_words_is_preserved_while_external_growth_is_parsed():
    matrix = [["Date", "지역", "인원 합계"], ["2024-01-31", "동부", 100],
              ["2024-02-29", "동부", 120], ["2024-03-31", "동부", 180]]
    result = ask(matrix, "지역별 인원 합계 이전 시점 대비 증감률 추이")
    assert result.status == "answered", result.model_dump()
    assert "20% → 50%" in result.answer


def test_filtered_share_numeric_predicate_ignores_unknown_historic_value_but_not_current():
    matrix = [["Date", "범주", "인원", "사업장"], ["2020-01-31", "A", None, "서울"],
              *[[date, category, value, "서울"] for date in ("2024-01-31", "2024-02-29")
                for category, value in (("A", 20), ("B", 80))]]
    question = "2024년 서울 사업장만 범주별 인원 10 이상 비중 추이"
    result = ask(matrix, question)
    assert result.status == "answered", result.model_dump()
    matrix[2][2] = None
    result = ask(matrix, question)
    assert result.status == "insufficient_evidence", result.model_dump()


@pytest.mark.parametrize("statistic", ["평균", "최솟값", "최댓값"])
def test_nonadditive_category_statistics_cannot_be_summed_into_whole(statistic):
    matrix = [["Date", "부서", "인원", "사업장"],
              *[[date, category, value, "서울"] for date in ("2024-01-31", "2024-02-29")
                for category, value in (("서비스", 20), ("서비스", 40), ("생산", 80))]]
    result = ask(matrix, f"서울 사업장만 전체 인원 중 서비스 부서 {statistic} 비중 추이")
    assert result.status == "insufficient_evidence", result.model_dump()
    assert result.verification.level != "request_checked"


def test_explicit_sum_with_duplicates_uses_original_whole_and_lineage():
    matrix = [["Date", "부서", "인원", "사업장"],
              *[[date, category, value, "서울"] for date in ("2024-01-31", "2024-02-29")
                for category, value in (("서비스", 20), ("서비스", 40), ("생산", 80))]]
    result = ask(matrix, "서울 사업장만 전체 인원 중 서비스 부서 합계 비중 추이")
    assert result.status == "answered", result.model_dump()
    assert "42.86%" in result.answer
    assert 140 not in {cell.value for cell in result.evidence}


def test_core_category_calculator_itself_rejects_nonadditive_aggregation():
    from app.agent.query.grouped_trend_sources import grouped_sources
    from app.agent.query.grouped_share_trend_calculations import category_share_points
    from app.agent.query.tabular_query_models import TabularFilter
    matrix = [["Date", "부서", "인원"],
              *[[date, category, value] for date in ("2024-01-31", "2024-02-29")
                for category, value in (("서비스", 20), ("서비스", 40), ("생산", 80))]]
    summary, index = table_fixture([(1, 1, matrix)])
    sources, named = grouped_sources("부서별 인원 평균 추이", summary, index)
    target = TabularFilter(column_id=sources[0].request.groups[0], operator="equals", value="서비스")
    with pytest.raises(ValueError, match="평균"):
        category_share_points(sources[0], target, named, index)


def test_joined_category_average_is_not_falsely_verified_as_whole_share():
    from tests.test_joined_trend_answers import answer
    sheets = {"이력": [["Date", "부서코드", "인원"],
                       *[[date, key, value] for date in ("2024-01-31", "2024-02-29")
                         for key, value in (("A", 20), ("A", 40), ("B", 80))]],
              "부서정보": [["부서코드", "부서", "사업장"], ["A", "서비스", "서울"], ["B", "생산", "서울"]]}
    result = answer(sheets, "이력과 부서정보를 부서코드로 연결해서 서울 사업장만 부서별 인원 평균 비중 추이")
    assert result.status == "insufficient_evidence", result.model_dump()
    assert result.verification.level != "request_checked"
