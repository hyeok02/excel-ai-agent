"""Match a period the user names ("2023년", "2022년 12월") to a plan's date filters.

A model writes "2023년" as Date ≥ 2023-01-01 and Date ≤ 2023-12-31. Those filters
are checked here against the period the request states: they must select exactly
that period, on a column whose source values are dates. Filters that do are the
request's own conditions; any other date filter remains unproven and the plan is
rejected by the ordinary checks.
"""
import re
from datetime import date, time, timedelta

from app.agent.query.tabular_filters import _date

_POINT = re.compile(r"((?:19|20)\d{2})\s*년(?:\s*(\d{1,2})\s*월)?(?:\s*(\d{1,2})\s*일)?"
                    r"|((?:19|20)\d{2})-(\d{2})(?:-(\d{2}))?")
_RANGE = re.compile(rf"({_POINT.pattern})\s*(?:부터|~|∼|–|—|에서)\s*({_POINT.pattern})(?:\s*까지)?")
LOWER = {"greater_than_or_equal", "greater_than"}
UPPER = {"less_than_or_equal", "less_than"}


def period_filters(text, plan, table):
    """Positions of plan filters that together select exactly a period stated in text."""
    asked = set(_periods(text))
    if not asked:
        return set()
    checked = set()
    for column in table.columns:
        kind = _date_column(table, column.id)
        positions = [index for index, item in enumerate(plan.filters)
                     if kind and item.column_id == column.id and _bound(item.value) is not None
                     and item.operator in LOWER | UPPER | {"equals"}]
        if positions and _interval([plan.filters[index] for index in positions], kind == "days") in asked:
            checked.update(positions)
    return checked


def without_periods(text):
    return _POINT.sub(" ", _RANGE.sub(" ", text))


def _periods(text):
    for match in _RANGE.finditer(text):
        first, second = _POINT.match(match.group(1)), _POINT.match(match.group(match.re.groups - 6))
        if first and second:
            yield _span(first)[0], _span(second)[1]
    for match in _POINT.finditer(_RANGE.sub(" ", text)):
        yield _span(match)


def _span(match):
    year, month, day = (match.group(1), match.group(2), match.group(3)) if match.group(1) else (
        match.group(4), match.group(5), match.group(6))
    year, month, day = int(year), int(month) if month else None, int(day) if day else None
    if day:
        start = date(year, month, day)
        return start, start + timedelta(days=1)
    if month:
        return date(year, month, 1), date(year + month // 12, month % 12 + 1, 1)
    return date(year, 1, 1), date(year + 1, 1, 1)


def _interval(filters, days_only):
    """[start, end) of days selected by date bounds on one column, or None if not whole days.

    "≤ 2022-12-31" and "≤ 2022-12-31T23:59:59" both end with that day. A
    "≤ 2022-12-31T00:00:00" bound ends with that day only when the source holds
    whole days; with clock times it would drop the day's later records.
    """
    start = end = None
    for item in filters:
        bound, kind = _bound(item.value)
        whole = kind == "day" and (days_only or isinstance(item.value, str) and len(item.value.strip()) == 10)
        next_day = bound + timedelta(days=1)
        if item.operator == "equals":
            low, high = (bound, next_day) if whole else (None, None)
        elif item.operator in LOWER:
            low, high = (next_day if item.operator == "greater_than" else bound) if kind == "day" else None, None
        elif item.operator == "less_than":
            low, high = None, bound if kind == "day" else None
        else:
            low, high = None, next_day if whole or kind == "end" else None
        if low is high is None:
            return None
        if low is not None:
            start = low if start is None else max(start, low)
        if high is not None:
            end = high if end is None else min(end, high)
    return (start, end) if start is not None and end is not None else None


def _bound(value):
    """(day, "day") for a date or midnight, (day, "end") for 23:59:59 or later; else None."""
    parsed = _date(value)
    if parsed is None:
        return None
    clock = parsed.time()
    if clock == time(0):
        return parsed.date(), "day"
    return (parsed.date(), "end") if clock >= time(23, 59, 59) else None


def _date_column(table, column):
    """"days" when every value is a whole day, "times" when some carry a clock time."""
    values = [_date(row.values.get(column)) for row in table.rows if row.values.get(column) not in (None, "")]
    if not values or any(value is None for value in values):
        return None
    return "days" if all(value.time() == time(0) for value in values) else "times"
