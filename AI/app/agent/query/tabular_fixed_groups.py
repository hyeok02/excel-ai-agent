"""A grouping fixed to one value by the plan's own filter is not a grouping.

"동부 지역 판매금액 합계" is sometimes planned as "by Region, where Region = East": one group,
the same rows and the same sum as "where Region = East". The grouping is dropped so the
request is checked as the single total it is. Nothing else about the plan changes.
"""
from dataclasses import replace

from app.agent.query.tabular_catalog import build_query_tables
from app.agent.query.verified_insight_constraints import _REQUIRED_CONCEPTS, contains_term
from app.agent.query.ambiguity_labels import resolve_unique_column

_OPERATIONS = {"numeric_summary", "row_count"}


def without_fixed_groups(intent, summary, question=""):
    return _top_of_list(_without_fixed_groups(intent, summary), summary, question)


def _top_of_list(intent, summary, question):
    """"보험가액이 가장 큰 계약은?" planned as an unordered list of one number column is its top row.

    Only a list whose selected columns hold exactly one numeric column is ordered by it, highest
    first for 가장 큰/높은/많은 and lowest first for 가장 작은/낮은/적은, and cut to one row.
    """
    plan = getattr(intent, "tabular_query", None)
    if plan is None or plan.operation != "row_list" or plan.order_by or plan.limit or plan.filter_expression:
        return intent
    asked = [index for index, group in enumerate(_REQUIRED_CONCEPTS[3:5])
             if any(contains_term(question.casefold(), alias) for alias in group)]
    tables = [table for table in build_query_tables(summary) if table.id == plan.table_id]
    if len(asked) != 1 or len(tables) != 1:
        return intent
    numeric = [column for column in plan.column_ids
               if (resolved := resolve_unique_column(column, tables[0])) is not None
               and any(isinstance(row.values.get(resolved), (int, float)) and not isinstance(row.values.get(resolved), bool)
                       for row in tables[0].rows)]
    if len(numeric) != 1:
        return intent
    ordered = plan.model_copy(update={"order_by": numeric[0], "descending": asked[0] == 0, "limit": 1})
    return replace(intent, tabular_query=ordered)


def _without_fixed_groups(intent, summary):
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
