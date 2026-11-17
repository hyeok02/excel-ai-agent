"""The column a "…별" word names is the grouping, when the plan grouped by another.

"주별 계약 건수" is sometimes planned as a count by Expiry, reading 주 as a week, in a table
that has a State column and no week. The word is read among the table's own column names by
the bounded label resolver; only a clear reading that names a different column moves the
grouping there. With no clear reading, or the plan's own column, nothing changes.
"""
import re
from dataclasses import replace

from app.agent.query.quota_errors import raise_for_quota_exhaustion
from app.agent.query.tabular_binding import bind_tabular_plan
from app.agent.query.tabular_catalog import build_query_tables
from app.agent.query.tabular_request_extras import _stated_subject

_GROUP_WORD = re.compile(r"(?<![가-힣])([가-힣]{1,8}별)(?:로)?(?![가-힣])")


async def regrouped(intent, summary, question, resolver=None):
    plan = getattr(intent, "tabular_query", None)
    words = list(dict.fromkeys(_GROUP_WORD.findall(question)))
    if plan is None or len(plan.group_by) != 1 or len(words) != 1 or plan.filter_expression is not None:
        return intent
    tables = [table for table in build_query_tables(summary) if table.id == plan.table_id]
    # The plan's sort key is often an alias ("sum_TotalPrice") that does not bind; it is kept as written.
    bound = bind_tabular_plan(plan.model_copy(update={"order_by": None, "limit": None}), tables[0]) if len(tables) == 1 else None
    if bound is None:
        return intent
    columns = {column.id: column for column in tables[0].columns}
    group = columns.get(bound.group_by[0])
    headers = [" ".join(column.header.split()) for column in tables[0].columns]
    if group is None or _stated_subject(question, group.header) or len(set(headers)) != len(headers):
        return intent  # the question writes the column's own name
    if resolver is None:
        from app.agent.query.tabular_source_alias_resolver import LangChainSourceLabelResolver
        resolver = LangChainSourceLabelResolver.from_environment()
    if resolver is None:
        return intent
    try:
        reading = await resolver.resolve(words[0], "column to group rows by", headers)
    except Exception as exception:
        raise_for_quota_exhaustion(exception)
        return intent
    if reading.status != "resolved" or type(reading.candidate_id) is not int or not 0 <= reading.candidate_id < len(headers):
        return intent
    named = tables[0].columns[reading.candidate_id]
    if named.id == group.id:
        return intent
    swap = lambda column: named.id if column == group.id else column
    return replace(intent, tabular_query=bound.model_copy(update={
        "group_by": [named.id], "column_ids": list(dict.fromkeys(swap(column) for column in bound.column_ids)),
        "identity_column_ids": list(dict.fromkeys(swap(column) for column in bound.identity_column_ids)),
        "order_by": named.id if plan.order_by in {group.id, group.header} else plan.order_by, "limit": plan.limit}))
