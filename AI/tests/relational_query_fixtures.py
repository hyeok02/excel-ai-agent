"""Source-derived multi-sheet fixtures without loading any user workbook."""
from dataclasses import replace

from app.agent.query.relational_execution import relational_query_answer
from app.agent.query.relational_models import RelationalQueryPlan
from app.agent.query.tabular_catalog import build_query_tables
from tests.tabular_query_fixtures import table_fixture


def relational_fixture(left=None, right=None, names=("Orders", "Customers"), offset=(1, 1)):
    left = left or [["Order ID", "Customer ID", "Amount"], ["ORD-1", "C1", 10], ["ORD-2", "C2", 20]]
    right = right or [["Customer ID", "Region"], ["C1", "North"], ["C2", "South"]]
    summaries, indices = [], []
    for matrix, name in zip((left, right), names):
        summary, index = table_fixture([(offset[0], offset[1], matrix)], sheet_name=name)
        summaries.append(summary)
        indices.append(index)
    summary = replace(summaries[0], sheet_count=2, sheets=[item.sheets[0] for item in summaries])
    index = replace(indices[0], rows=indices[0].rows + indices[1].rows,
                    indexed_cell_count=sum(item.indexed_cell_count for item in indices))
    return summary, index


def relational_plan(summary, **changes):
    left, right = build_query_tables(summary)
    values = dict(operation="numeric_summary", left_table_id=left.id, right_table_id=right.id,
                  on=[{"left_column_id": left.columns[1].id, "right_column_id": right.columns[0].id}],
                  column_ids=[f"left.{left.columns[2].id}"], group_by=[f"right.{right.columns[1].id}"])
    values.update(changes)
    return RelationalQueryPlan(**values)


def answer(summary, index, question="Orders와 Customers를 Customer ID로 연결해서 Region별 Amount 합계", **changes):
    return relational_query_answer(relational_plan(summary, **changes), summary, index, question)
