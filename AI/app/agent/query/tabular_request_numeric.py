"""Match stated numeric thresholds, operators and percent display scales."""
import re
from decimal import Decimal, InvalidOperation

from app.agent.query.excel_number_formats import parse_number_format

_NUMBER = r"-?\d[\d,]*(?:\.\d+)?"
_UNIT = r"(?:%|퍼센트|percent)?"
_OPS = {
    "이상": "greater_than_or_equal", "초과": "greater_than",
    "이하": "less_than_or_equal", "미만": "less_than",
    "보다 큰": "greater_than", "보다 작은": "less_than",
    ">=": "greater_than_or_equal", "≥": "greater_than_or_equal",
    "<=": "less_than_or_equal", "≤": "less_than_or_equal",
    ">": "greater_than", "<": "less_than", "=": "equals",
    "at least": "greater_than_or_equal", "at most": "less_than_or_equal",
    "greater than": "greater_than", "more than": "greater_than", "above": "greater_than",
    "less than": "less_than", "below": "less_than", "equal to": "equals",
}
_SUFFIX = re.compile(rf"(?P<number>{_NUMBER})\s*(?P<unit>{_UNIT})\s*(?P<op>이상|초과|이하|미만|보다\s+큰|보다\s+작은)", re.I)
_PREFIX = re.compile(rf"(?P<op>>=|<=|≥|≤|>|<|=|at least|at most|greater than|more than|less than|above|below|equal to)\s*(?P<number>{_NUMBER})\s*(?P<unit>{_UNIT})", re.I)
_PERCENT_EQUALS = re.compile(rf"(?P<number>{_NUMBER})\s*(?P<unit>%|퍼센트|percent)\s*(?:인|와 같은|와 동일한|equal)", re.I)


def numeric_constraints_match(text, plan, table, rank_filters=frozenset()):
    requests = []
    for pattern in (_SUFFIX, _PREFIX, _PERCENT_EQUALS):
        for match in pattern.finditer(text):
            operation = _OPS.get(" ".join((match.groupdict().get("op") or "=").casefold().split()))
            request = (match.start(), match.end(), operation, _number(match.group("number")), bool(match.group("unit")))
            if request not in requests:
                requests.append(request)
    checked = set(rank_filters)
    for start, end, operator, value, percent in requests:
        column = _preceding_column(text, start, table)
        matches = []
        for position, condition in enumerate(plan.filters):
            if condition.operator != operator or _number(condition.value) is None:
                continue
            if column is not None and condition.column_id != column:
                continue
            if _threshold_matches(condition, value, percent, table):
                matches.append(position)
        if not matches:
            return False
        checked.update(matches)
    # Extra numeric predicates also change the population, even when the model
    # retained every condition the user did request.
    comparisons = {"greater_than", "greater_than_or_equal", "less_than", "less_than_or_equal"}
    for position, condition in enumerate(plan.filters):
        if position in checked:
            continue
        if condition.operator in comparisons:
            return False
        if condition.operator in {"equals", "not_equals"} and _number(condition.value) is not None:
            if not _explicit_equality(text, condition, plan.operation):
                return False
    return True


def _explicit_equality(text, condition, operation):
    value = str(condition.value).replace(",", "")
    plain = text.replace(",", "")
    match = re.search(rf"(?<![A-Za-z0-9]){re.escape(value)}(?![0-9])", plain)
    if match is None:
        return False
    after = plain[match.end():match.end() + 15]
    before = plain[max(0, match.start() - 15):match.start()]
    negative = bool(re.search(r"아닌|제외|\bnot\b|!=|≠", before + after, re.I))
    if condition.operator == "not_equals":
        return negative
    return not negative and (operation == "lookup" or bool(re.match(r"\s*(?:인|이[며고]|와\s*같은)", after))
                             or bool(re.search(r"=\s*$|equal\s+to\s*$", before, re.I)))


def _threshold_matches(condition, requested, percent, table):
    actual = _number(condition.value)
    if actual is None or requested is None:
        return False
    column = next(column for column in table.columns if column.id == condition.column_id)
    formats = [parse_number_format(row.number_formats.get(column.id, "General")) for row in table.rows]
    percentage_column = ("%" in column.header or "percent" in column.header.casefold()
                         or (formats and all(style.percent for style in formats)))
    if not percent:
        return actual == requested
    if not percentage_column:
        return False
    if condition.value_unit == "percent":
        return actual == requested
    multipliers = {style.multiplier for style in formats}
    return len(multipliers) == 1 and actual * next(iter(multipliers)) == requested


def _preceding_column(text, position, table):
    found = []
    for column in table.columns:
        for match in re.finditer(re.escape(column.header), text, re.I):
            if match.end() <= position and position - match.end() <= 80:
                found.append((match.end(), column.id))
    return max(found, default=(0, None))[1]


def _number(value):
    if isinstance(value, bool) or value is None:
        return None
    try:
        number = Decimal(str(value).replace(",", ""))
        return number if number.is_finite() else None
    except (ValueError, InvalidOperation):
        return None
