"""A grouping fixed to one value by the plan's own filter is not a grouping.

"동부 지역 판매금액 합계" is sometimes planned as "by Region, where Region = East": one group,
the same rows and the same sum as "where Region = East". The grouping is dropped so the
request is checked as the single total it is. Nothing else about the plan changes.
"""
from dataclasses import replace

from app.agent.query.tabular_catalog import build_query_tables
from app.agent.query.ambiguity_labels import resolve_unique_column

_OPERATIONS = {"numeric_summary", "row_count"}


def without_fixed_groups(intent, summary):
    plan = getattr(intent, "tabular_query", None)
    if (plan is None or not plan.group_by or plan.operation not in _OPERATIONS
            or plan.filter_expression is not None or plan.having or plan.share_of_total
            or plan.relative_rank is not None or plan.per_group_limit is not None):
        return intent
    tables = [table for table in build_query_tables(summary) if table.id == plan.table_id]
    if len(tables) != 1:
        return intent
    fixed = {resolve_unique_column(item.column_id, tables[0]) for item in plan.filters if item.operator == "equals"}
    kept = [column for column in plan.group_by if resolve_unique_column(column, tables[0]) not in fixed]
    if len(kept) == len(plan.group_by) or None in fixed:
        return intent
    order = plan.order_by if plan.order_by not in plan.group_by else None
    return replace(intent, tabular_query=plan.model_copy(update={"group_by": kept, "order_by": order}))
