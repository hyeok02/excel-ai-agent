"""Read "Cookies랑 Crackers" as either value of one column, never as two conditions on it.

A row holds one Category, so values of the same text column listed with 랑/와/과/하고/및/,/또는
can only mean rows with any of them. Values must be exact source values; a reading the
translated-filter path wrote ("쿠키(Cookies)") is accepted around a value.
"""
import re

from app.agent.query.boolean_filter_models import BooleanFilterExpression as Node
from app.agent.query.tabular_query_models import TabularFilter

_JOINER = r"\s*(?:,|및|또는|혹은|이랑|하고|랑|와|과|\bor\b|\band\b)\s*"
MAX_VALUES = 8


def value_list(question, table):
    """(filters, OR expression, remainder) for the one listed run of a column's values, or None."""
    found = []
    for column in table.columns:
        values = {value for row in table.rows if isinstance(value := row.values.get(column.id), str)
                  and value.strip() and len(value) <= 100 and not re.search(r"[()]", value)}
        if len(values) < 2:
            continue
        names = "|".join(re.escape(value) for value in sorted(values, key=len, reverse=True))
        item = rf"(?:[가-힣A-Za-z0-9]+\((?:{names})\)|(?:{names}))"
        for match in re.finditer(rf"(?<![\w]){item}(?:{_JOINER}{item})+(?![A-Za-z0-9_])", question, re.I):
            listed = [hit.group() for hit in re.finditer(rf"(?<![A-Za-z0-9_])(?:{names})(?![A-Za-z0-9_])",
                                                         match.group(), re.I)]
            canonical = {value.casefold(): value for value in values}
            listed = list(dict.fromkeys(canonical[value.casefold()] for value in listed))
            if 2 <= len(listed) <= MAX_VALUES:
                found.append((column, listed, match))
    if len(found) != 1:
        return None  # none, or two lists that could each be the condition
    column, listed, match = found[0]
    filters = [TabularFilter(column_id=column.id, operator="equals", value=value) for value in listed]
    expression = Node(operator="or", children=[Node(operator="predicate", filter_index=index)
                                               for index in range(len(filters))])
    remainder = question[:match.start()] + " " * (match.end() - match.start()) + question[match.end():]
    return filters, expression, remainder
