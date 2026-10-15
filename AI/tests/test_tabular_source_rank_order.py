"""Stored ranks may select top-N only when the requested metric proves them."""
from dataclasses import replace

import pytest

from app.agent.query.tabular_catalog import build_query_tables
from app.agent.query.tabular_query_models import TabularFilter, TabularQueryPlan
from app.agent.query.tabular_request_constraints import matches_constraints
from tests.tabular_query_fixtures import table_fixture


def _ranked_table():
    summary, _ = table_fixture([(8, 3, [
        ["Position", "Holder", "Weight (%)"], [3, "North", 5],
        [1, "South", 12], [4, "East", 2], [2, "West", 8],
    ])], sheet_name="Moved observations")
    return build_query_tables(summary)[0]


@pytest.mark.parametrize("question,descending", [
    ("Weight (%) 상위 2개 합계", False),
    ("Weight (%) 하위 2개 합계", True),
])
def test_source_rank_sort_matches_requested_metric_top_or_bottom(question, descending):
    table = _ranked_table()
    plan = TabularQueryPlan(operation="numeric_summary", table_id=table.id, column_ids=["E"],
                            statistic="sum", order_by="C", descending=descending, limit=2)
    assert matches_constraints(question, plan, table, [table])


@pytest.mark.parametrize("values", [(5, 12, 20, 8), (5, 1, 2, 8)])
def test_stale_source_ranks_cannot_override_the_requested_numeric_metric(values):
    table = _ranked_table()
    table = replace(table, rows=tuple(replace(row, values={**row.values, "E": value})
                                      for row, value in zip(table.rows, values)))
    plan = TabularQueryPlan(operation="numeric_summary", table_id=table.id, column_ids=["E"],
                            statistic="sum", order_by="C", descending=False, limit=2)
    assert not matches_constraints("Weight (%) 상위 2개 합계", plan, table, [table])


def test_a_non_rank_numeric_sort_still_cannot_substitute_for_the_requested_metric():
    table = _ranked_table()
    table = replace(table, rows=tuple(replace(row, values={**row.values, "C": row.values["C"] * 10})
                                      for row in table.rows))
    plan = TabularQueryPlan(operation="numeric_summary", table_id=table.id, column_ids=["E"],
                            statistic="sum", order_by="C", descending=False, limit=2)
    assert not matches_constraints("Weight (%) 상위 2개 합계", plan, table, [table])


def test_rank_filter_and_rank_sort_do_not_also_require_a_redundant_limit():
    table = _ranked_table()
    plan = TabularQueryPlan(operation="numeric_summary", table_id=table.id, column_ids=["E"],
                            statistic="sum", order_by="C", descending=False, filters=[
                                TabularFilter(column_id="C", operator="less_than_or_equal", value=2),
                            ])
    assert matches_constraints("Weight (%) 상위 2개 합계", plan, table, [table])
