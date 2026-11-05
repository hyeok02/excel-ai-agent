"""Source rows a rule's conditions select, including date ranges on date columns."""
import re
from datetime import datetime

from app.agent.query.tabular_filters import filtered_rows

COMPARE = {"greater_than": lambda a, b: a > b, "greater_than_or_equal": lambda a, b: a >= b,
           "less_than": lambda a, b: a < b, "less_than_or_equal": lambda a, b: a <= b}


def matching_rows(table, filters):
    """Source filters, plus date ranges ("2023년" → 2023-01-01 ≤ Date < 2024-01-01)."""
    dates = [item for item in filters if item.operator in COMPARE and _date(item.value) is not None]
    rows = filtered_rows(table, [item for item in filters if item not in dates])
    for item in dates if rows is not None else ():
        values = [_date(row.values.get(item.column_id)) for row in rows]
        if any(value is None for value in values):
            return None  # a blank or non-date cell cannot be placed inside a date range
        rows = [row for row, value in zip(rows, values) if COMPARE[item.operator](value, _date(item.value))]
    return rows


def shown(value):
    if value is None:
        return ""
    return re.sub(r"[T ]00:00(?::00)?$", "", value) if isinstance(value, str) else str(value)


def _date(value):
    if isinstance(value, datetime):
        return value
    if isinstance(value, str) and re.fullmatch(r"\d{4}-\d{2}-\d{2}(?:[T ]\d{2}:\d{2}(?::\d{2})?)?", value.strip()):
        return datetime.fromisoformat(value.strip())
    return None
