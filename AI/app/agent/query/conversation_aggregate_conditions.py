"""Reuse only independently revalidated conditions for an explicit follow-up."""
import re

from app.agent.query.conversation_models import ContextResolutionDraft
from app.agent.query.references import _box, _contains
from app.agent.query.source_aggregate_answers import source_aggregate_plan
from app.agent.query.tabular_catalog import build_query_tables
from app.agent.query.tabular_execution import execute_tabular_query

SAME_CONDITIONS = re.compile(r"^(?:그|같은|동일한)\s*조건(?:에서|으로)\s*")
_OPERATORS = {"equals": "=", "not_equals": "!=", "greater_than": ">",
              "greater_than_or_equal": ">=", "less_than": "<", "less_than_or_equal": "<="}


def bound_aggregate_conditions(question, context, entries, summary, index):
    prefix = SAME_CONDITIONS.match(question.strip())
    if prefix is None or not context.turns or context.turns[-1].needs_clarification:
        return None
    latest = f"turn:{len(context.turns)-1}"
    entry = next((item for item in entries if item["id"] == latest), None)
    if entry is None:
        return None
    requested = question.strip()[prefix.end():]
    candidates = []
    for table in build_query_tables(summary):
        bounds = _box(table.id)
        if bounds is None or not any((cell := _box(item["reference"])) and _contains(bounds, cell)
                                     for item in entry["source_cells"]):
            continue
        previous = source_aggregate_plan(context.turns[-1].question, table)
        current = source_aggregate_plan(requested, table)
        if previous is None or not previous.filters or current is None or current.filters:
            continue
        # Re-read the old request, not its answer text. Unknown conditions,
        # stale source scopes and ambiguous plans must not become trusted context.
        if execute_tabular_query(previous, summary, index, context.turns[-1].question) is None:
            continue
        conditions = []
        columns = {column.id: column.header for column in table.columns}
        for condition in previous.filters:
            label, value = columns[condition.column_id], condition.value
            operator = _OPERATORS.get(condition.operator)
            if operator is None or isinstance(value, bool) or value is None:
                break
            if any(character in str(label) + str(value) for character in "\"'\n\r"):
                break
            literal = f'"{value}"' if isinstance(value, str) else str(value)
            if condition.value_unit == "percent":
                literal += "%"
            conditions.append(f'"{label}" {operator} {literal}')
        else:
            resolved = f"{table.sheet_name} 시트에서 {' and '.join(conditions)} {requested}"
            rebound = source_aggregate_plan(resolved, table)
            if rebound is not None and execute_tabular_query(rebound, summary, index, resolved) is not None:
                candidates.append(resolved)
    if len(candidates) != 1 or len(candidates[0]) > 1000:
        return None
    return ContextResolutionDraft(status="resolved", question=candidates[0], context_ids=[latest])
