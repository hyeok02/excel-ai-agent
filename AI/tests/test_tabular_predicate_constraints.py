"""Detailed constraints must not be lost between a request and its plan."""
from dataclasses import replace

import pytest

from app.agent.query.tabular_catalog import build_query_tables
from app.agent.query.tabular_query_models import TabularFilter, TabularQueryPlan
from app.agent.query.tabular_request_constraints import matches_constraints
from tests.tabular_query_fixtures import table_fixture
from tests.test_tabular_request_adversarial import _answer, _fixture


def test_model_limit_cannot_hide_an_ambiguous_duplicate_lookup():
    summary, index = table_fixture([(2, 2, [
        ["Record ID", "Amount"], ["ORDER50001", 10], ["ORDER50001", 900],
    ])])
    plan = TabularQueryPlan(operation="lookup", table_id=build_query_tables(summary)[0].id,
                            column_ids=["C"], limit=1, filters=[
                                TabularFilter(column_id="B", operator="equals", value="ORDER50001"),
                            ])

    assert _answer("ORDER50001의 Amount", plan, summary, index, "cell_lookup") is None


def test_disjunction_cannot_be_executed_as_intersection():
    summary, index = _fixture()
    plan = TabularQueryPlan(operation="row_count", table_id=build_query_tables(summary)[0].id,
                            filters=[
                                TabularFilter(column_id="D", operator="equals", value="Done"),
                                TabularFilter(column_id="D", operator="equals", value="Pending"),
                            ])

    assert _answer("Status가 Done 또는 Pending인 건수", plan, summary, index, "row_count") is None


def test_percent_equality_cannot_compare_display_points_to_raw_fractions():
    summary, index = table_fixture([(1, 1, [
        ["Owner", "Share (%)"], ["A", 0.25], ["B", 0.1],
    ])])
    for row in summary.sheets[0].regions[0].analysis_rows[1:]:
        row[1]["number_format"] = "0.0%"
    index = replace(index, rows=tuple(replace(row, cells=tuple(
        replace(cell, number_format="0.0%") if cell.address.startswith("B") and row.row_number > 1 else cell
        for cell in row.cells)) for row in index.rows))
    plan = TabularQueryPlan(operation="row_count", table_id=build_query_tables(summary)[0].id,
                            filters=[TabularFilter(column_id="B", operator="equals", value=25,
                                                   value_unit="percent")])
    answer = _answer("Share (%)가 25%인 건수", plan, summary, index, "row_count")

    assert answer is None or "1건" in answer.answer


@pytest.mark.parametrize("question,operator,value", [
    ("Amount가 100 초과인 건수", "greater_than", 100),
    ("Amount가 100 이상인 건수", "greater_than_or_equal", 100),
    ("Amount가 200 미만인 건수", "less_than", 200),
    ("Amount가 200 이하인 건수", "less_than_or_equal", 200),
    ("Amount greater than 100 count", "greater_than", 100),
])
def test_correct_numeric_request_constraints_remain_supported(question, operator, value):
    summary, _ = _fixture()
    table = build_query_tables(summary)[0]
    plan = TabularQueryPlan(operation="row_count", table_id=table.id,
                            filters=[TabularFilter(column_id="E", operator=operator, value=value)])

    assert matches_constraints(question, plan, table, [table])


def test_top_n_source_rank_requires_independently_matching_metric_order():
    summary, _ = table_fixture([(4, 3, [
        ["Rank", "Owner", "Weight (%)"], [1, "North", 12],
        [2, "South", 8], [3, "East", 5], [4, "West", 2],
    ])])
    table = build_query_tables(summary)[0]
    plan = TabularQueryPlan(operation="numeric_summary", table_id=table.id,
                            column_ids=["E"], statistic="sum", filters=[
                                TabularFilter(column_id="C", operator="less_than_or_equal", value=3),
                            ])
    assert matches_constraints("Weight (%) 상위 3개 합계", plan, table, [table])
    wrong_rows = (replace(table.rows[0], values={**table.rows[0].values, "E": 1}), *table.rows[1:])
    wrong_table = replace(table, rows=wrong_rows)
    assert not matches_constraints("Weight (%) 상위 3개 합계", plan, wrong_table, [wrong_table])


def test_source_top_n_title_does_not_add_a_ranking_request():
    summary, _ = _fixture()
    table = replace(build_query_tables(summary)[0], context=(("Renamed Records!C2", "TOP 30 RECORDS"),))
    plan = TabularQueryPlan(operation="row_count", table_id=table.id,
                            filters=[TabularFilter(column_id="D", operator="equals", value="Done")])

    assert matches_constraints("TOP 30 RECORDS에서 Status가 Done인 건수", plan, table, [table])


def test_percent_threshold_accepts_points_and_requires_fractional_conversion():
    summary, _ = table_fixture([(1, 1, [["Owner", "Share (%)"], ["A", 1.1], ["B", 0.9]])])
    table = build_query_tables(summary)[0]
    plan = TabularQueryPlan(operation="row_count", table_id=table.id,
                            filters=[TabularFilter(column_id="B", operator="greater_than_or_equal", value=1)])
    assert matches_constraints("Share (%)가 1% 이상인 건수", plan, table, [table])
    fractional = replace(table, rows=tuple(replace(row, number_formats={"B": "0.0%"}) for row in table.rows))
    assert not matches_constraints("Share (%)가 1% 이상인 건수", plan, fractional, [fractional])
    plan.filters[0].value_unit = "percent"
    assert matches_constraints("Share (%)가 1% 이상인 건수", plan, fractional, [fractional])


def test_top_n_cannot_sort_another_numeric_column_that_is_also_selected():
    summary, index = table_fixture([(1, 1, [
        ["Owner", "Amount", "Score"], ["A", 100, 5], ["B", 200, 3], ["C", 300, 1],
    ])])
    table = build_query_tables(summary)[0]
    plan = TabularQueryPlan(operation="row_list", table_id=table.id, column_ids=["B", "C"],
                            order_by="C", limit=2)

    assert _answer("Amount 상위 2개 행의 Amount와 Score", plan, summary, index, "row_list") is None
