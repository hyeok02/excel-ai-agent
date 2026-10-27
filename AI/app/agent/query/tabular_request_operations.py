"""Check that the requested quantity is one the planned operation can produce.

Only grammar is used here: statistic, change and count wording. Source labels
and plan filter values are removed first, so a field named "합계" or a category
"평균 이하" is a source scope, not a request for a different operation.
"""
import re

from app.agent.query.ambiguity_labels import label_base
from app.agent.query.tabular_request_literals import without_literals

STATISTICS = {
    "sum": r"합계|총합|합산|모두\s*더해|전부\s*더해|\bsum\b|\btotal\b",
    "average": r"평균|\baverage\b|\bmean\b",
    "min": r"최솟값|최소값|\bminimum\b",
    "max": r"최댓값|최대값|\bmaximum\b",
}
_CHANGE = r"증감|변화|변동|추이|증가율|감소율|\b(?:changes?|growth|trend)\b"
_COUNT = r"몇\s*(?:건|개|명|곳|가지|행)|건수|개수|행\s*수|\bhow\s+many\b|\b(?:count|number)\s+of\b"
_COUNTING = {"row_count", "distinct_count", "frequencies"}


def operation_matches(text, plan, table):
    text = _request_grammar(text, table)
    requested = {key for key, pattern in STATISTICS.items() if re.search(pattern, text, re.I)}
    if plan.operation == "numeric_summary":
        if not _statistic_matches(requested, plan):
            return False
    elif plan.operation != "lookup":
        # Counts, distributions and row lists cannot produce a sum, mean or
        # extreme value. A stored lookup cell may itself be that statistic.
        scopes = [str(item.value) for item in plan.filters if isinstance(item.value, str)]
        requested = {key for key in requested
                     if not any(re.search(STATISTICS[key], value, re.I) for value in scopes)}
        if plan.operation in _COUNTING and (re.search(_COUNT, text, re.I)
                                            or not re.search(r"합계|총합|\bsum\b", text, re.I)):
            requested.discard("sum")  # "건수 합계", "total number of rows"
        if requested or plan.operation == "row_list" and re.search(_COUNT, text, re.I):
            return False
    return _change_matches(text, plan, table)


def _statistic_matches(requested, plan):
    if getattr(plan, "group_by", ()):
        if getattr(plan, "share_of_total", False) and not requested:
            return plan.statistic == "sum"
        return (not requested and plan.statistic == "all") or requested == {plan.statistic}
    return not requested or plan.statistic == "all" or requested == {plan.statistic}


def _change_matches(text, plan, table):
    """A change needs two observations: groups, several value fields, or a
    source field/category that itself records the change."""
    if not re.search(_CHANGE, text, re.I) or getattr(plan, "group_by", ()):
        return True
    involved = set(plan.column_ids) | {item.column_id for item in plan.filters}
    labels = [column.header for column in table.columns if column.id in involved]
    labels += [str(item.value) for item in plan.filters]
    return len(plan.column_ids) > 1 or any(re.search(_CHANGE, str(label), re.I) for label in labels)


def _request_grammar(text, table):
    text = without_literals(text)
    labels = {label for column in table.columns for label in (column.header, label_base(column.header))}
    for label in sorted(labels, key=len, reverse=True):
        # An isolated operator/column-name collision is ambiguous, not proof
        # that the user did not ask for an aggregate.
        if not any(re.fullmatch(pattern, label, re.I) for pattern in STATISTICS.values()):
            text = re.sub(r"(?<![\w])" + re.escape(label) + r"(?![A-Za-z0-9_])", " ", text, flags=re.I)
    return text
