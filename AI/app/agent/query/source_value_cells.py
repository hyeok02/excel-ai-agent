"""Cell-value predicates shared by the source value lookup."""
import re
from datetime import date, datetime

_EMPTY = {"", "na", "n/a", "nm", "-", "--", "none", "null"}


def usable(value):
    text = " ".join(str(value).split()) if value is not None else ""
    return value is not None and text.casefold() not in _EMPTY and not text.startswith("#")


def is_number(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def as_date(value):
    if isinstance(value, datetime):
        return value
    if isinstance(value, date):
        return datetime(value.year, value.month, value.day)
    if isinstance(value, str) and re.fullmatch(r"\d{4}-\d{2}-\d{2}(?:[T ][\d:.]+)?", value.strip()):
        return datetime.fromisoformat(value.strip()[:10])
    return None


def matches(day, period):
    year, month = period
    return day.year == year and (month is None or day.month == month)
