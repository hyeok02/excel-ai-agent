"""Schema-bound condition spans cannot erase unhandled parts of a question."""
import pytest

from app.agent.query.grouped_trend_request import parse_grouped_request
from app.agent.query.tabular_catalog import build_query_tables
from app.agent.query.trend_source_readback import column_cells, table_rows
from tests.support.large_workbook_fixtures import offline
from tests.test_grouped_trend_adversarial import grouped
from tests.tabular_query_fixtures import table_fixture


def parsed(question, matrix=None):
    summary, index = table_fixture([(1, 1, matrix or grouped())])
    tables = build_query_tables(summary)
    table = tables[0]
    rows, error = table_rows(table, tables, index, question)
    assert error is None
    return parse_grouped_request(question, table, [column_cells(row) for row in rows[1:]], "C", "A")


@pytest.mark.parametrize("question", [
    "서울 사업장만 부서별 인원 추이를 비교해줘",
    "사업장이 서울인 부서별 인원 추이를 비교해줘",
])
def test_schema_bound_literal_before_or_after_field_is_consumed(question):
    request = parsed(question)
    assert request.groups == ("B",)
    assert [(condition.column_id, condition.operator, condition.value) for condition in request.filters] == [
        ("D", "equals", "서울")]
    assert "서울" not in request.residual and "사업장" not in request.residual
    assert "부서별" not in request.residual and "인원" in request.residual


@pytest.mark.parametrize("phrase, operator", [("100 이상", "greater_than_or_equal"), ("> 100", "greater_than")])
def test_numeric_predicate_keeps_the_metric_and_date_scope(phrase, operator):
    request = parsed(f"2024년 인원 {phrase}인 기간만 추이를 설명해줘")
    assert request.filters[0].column_id == "C" and request.filters[0].operator == operator
    assert request.filters[0].value == 100 and "100" not in request.residual
    assert "2024년" in request.residual and "인원" in request.residual


def test_unhandled_condition_is_not_erased_by_a_handled_predicate():
    request = parsed("서울 사업장만 부서별 인원 추이와 내년 예상 인원을 설명해줘")
    assert "내년 예상" in request.residual
    request = parsed("서울 사업장만 없는등급인 부서별 인원 추이를 비교해줘")
    assert "없는등급" in request.residual


def test_schema_column_can_appear_in_multi_dimension_grouping():
    request = parsed("사업장 및 부서별 인원 합계 추이를 비교해줘")
    assert request.groups == ("D", "B") and request.statistic == "sum"
    assert "사업장" not in request.residual and "부서" not in request.residual


def test_english_grouping_uses_source_labels():
    matrix = [["Date", "Division", "Employees", "Site"],
              ["2024-01-01", "Blue", 10, "North"], ["2024-02-01", "Blue", 20, "North"]]
    request = parsed("Employees trend grouped by Division and Site", matrix)
    assert request.groups == ("B", "D") and "Employees" in request.residual


@pytest.mark.parametrize("question", [
    "서울 또는 부산 사업장만 부서별 인원 추이를 비교해줘",
    "부서별 인원 합계와 평균 추이를 비교해줘",
    "100 이상인 부서별 인원 추이를 비교해줘",
])
def test_unsupported_or_unbound_conditions_raise(question):
    with pytest.raises(ValueError):
        parsed(question)


def test_repeated_source_literal_needs_a_field_binding():
    matrix = [["Date", "부서", "인원", "사업장"],
              ["2024-01-01", "서울", 10, "서울"], ["2024-02-01", "서울", 20, "서울"]]
    with pytest.raises(ValueError):
        parsed("서울 인원 추이를 설명해줘", matrix)


def test_plain_trend_is_left_to_existing_handler():
    assert parsed("인원 추이를 설명해줘") is None


def test_unique_source_category_can_qualify_metric_without_repeating_its_field():
    request = parsed("서울 인원 추이를 설명해줘")
    assert request.filters[0].column_id == "D" and request.filters[0].value == "서울"
    assert "인원" in request.residual


def test_negative_category_condition_before_header_keeps_operator():
    request = parsed("서울 아닌 사업장만 부서별 인원 추이를 비교해줘")
    assert request.filters[0].operator == "not_equals"
    assert "서울" not in request.residual and "사업장" not in request.residual


@pytest.mark.parametrize("header", ["인원 100 이상", "Employees Average", "Q1 Employees"])
def test_operator_words_inside_metric_header_do_not_create_filters_or_aggregates(header):
    matrix = grouped()
    matrix[0][2] = header
    assert parsed(f"{header} 추이를 설명해줘", matrix) is None


@pytest.mark.parametrize("value", ["Sum", "Average", "인원 100 이상"])
def test_source_category_operation_words_are_not_extra_operations(value):
    matrix = grouped()
    for row in matrix[1:]:
        row[3] = value
    request = parsed(f"{value} 사업장만 부서별 인원 추이를 비교해줘", matrix)
    assert request.statistic is None and len(request.filters) == 1
    assert request.filters[0].value == value
