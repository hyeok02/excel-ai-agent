"""Prove predicates over explicitly labelled numeric buckets, not guessed values.

A source bucket such as "12 and beyond" is not the number 12. A predicate is
known only when every represented value satisfies it, or every value fails it.
Intersecting boundaries stay unknown so bucket aggregates are never prorated.
"""
import re
from decimal import Decimal

_NUMBER = r"[-+]?(?:\d+(?:\.\d+)?|\d{1,3}(?:,\d{3})+(?:\.\d+)?)"
_LOWER = re.compile(rf"(?P<number>{_NUMBER})\s*(?:and\s+(?:beyond|above|over)|or\s+(?:more|greater)|이상)", re.I)
_UPPER = re.compile(rf"(?P<number>{_NUMBER})\s*(?:and\s+(?:below|under)|or\s+(?:less|fewer)|이하)", re.I)
_OPEN_LOWER = re.compile(rf"(?:more\s+than|greater\s+than|above|over)\s+(?P<number>{_NUMBER})|(?P<korean>{_NUMBER})\s*초과", re.I)
_OPEN_UPPER = re.compile(rf"(?:less\s+than|below|under)\s+(?P<number>{_NUMBER})|(?P<korean>{_NUMBER})\s*미만", re.I)


def source_numeric_interval(value):
    if not isinstance(value, str):
        return None
    text = value.strip()
    for pattern, lower, inclusive in [(_LOWER, True, True), (_UPPER, False, True),
                                      (_OPEN_LOWER, True, False), (_OPEN_UPPER, False, False)]:
        match = pattern.fullmatch(text)
        if match:
            number = Decimal((match["number"] or match.groupdict().get("korean")).replace(",", ""))
            return (number, inclusive, Decimal("Infinity"), False) if lower else (
                Decimal("-Infinity"), False, number, inclusive)
    return None


def interval_comparison(interval, operator, threshold):
    lower, lower_closed, upper, upper_closed = interval
    target = Decimal(str(threshold))
    if operator in {"less_than", "less_than_or_equal"}:
        reverse = "greater_than_or_equal" if operator == "less_than" else "greater_than"
        result = interval_comparison(interval, reverse, threshold)
        return None if result is None else not result
    if operator == "greater_than_or_equal":
        if lower >= target:
            return True
        if upper < target or upper == target and not upper_closed:
            return False
        return None
    if operator == "greater_than":
        if lower > target or lower == target and not lower_closed:
            return True
        if upper <= target:
            return False
        return None
    if operator in {"equals", "not_equals"}:
        outside = (target < lower or target > upper or target == lower and not lower_closed
                   or target == upper and not upper_closed)
        return operator == "not_equals" if outside else None
    return None
