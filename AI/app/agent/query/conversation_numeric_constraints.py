"""Preserve explicit signs and symbolic predicates across context rewrites."""
from collections import Counter
import re

_NUMBER = re.compile(r"\d+(?:[.,]\d+)*")
_VALUE = r"(?P<sign>[-+−]?)\s*(?P<number>\d+(?:[.,]\d+)*)\s*(?P<percent>%?)"
_OPERATOR = r">=|<=|!=|==|<>|≥|≤|≠|>|<|="
_COMPARISON = re.compile(
    rf"(?P<operator>{_OPERATOR}|at least|at most|greater than|more than|less than|above|below|equal to)\s*"
    + _VALUE, re.I,
)
_SUFFIX = re.compile(_VALUE + r"\s*(?P<operator>이상|초과|이하|미만|보다\s+큰|보다\s+작은)")
_LEFT_VALUE = re.compile(_VALUE + rf"\s*(?P<operator>{_OPERATOR})(?![=<>])(?!\s*[-+−]?\s*\d)")
_EQUIVALENT = {
    "≥": ">=", "≤": "<=", "≠": "!=", "<>": "!=", "==": "=",
    "이상": ">=", "초과": ">", "이하": "<=", "미만": "<", "보다 큰": ">", "보다 작은": "<",
    "at least": ">=", "at most": "<=", "greater than": ">", "more than": ">",
    "less than": "<", "above": ">", "below": "<", "equal to": "=",
}
_REVERSED = {">": "<", "<": ">", ">=": "<=", "<=": ">=", "=": "=", "!=": "!="}


def numeric_constraints_preserved(original, rewritten):
    # A numeric magnitude alone is not enough: -10 must never become 10, or
    # >10 become <10. Additional context numbers may legitimately be inserted.
    if not _signed_numbers(original) <= _signed_numbers(rewritten):
        return False
    return _comparisons(original) <= _comparisons(rewritten)


def _signed_numbers(text):
    result = Counter()
    for match in _NUMBER.finditer(text):
        prefix = text[:match.start()].rstrip()
        sign = 1
        if prefix.endswith(("-", "−")):
            preceding = prefix[:-1].rstrip()
            # Hyphens inside dates and record IDs are separators, not signs.
            if not preceding or not preceding[-1].isalnum() or len(prefix) > 1 and prefix[-2].isspace():
                sign = -1
        result[(match.group(), sign)] += 1
    return result


def _comparisons(text):
    result = Counter()
    for pattern in (_COMPARISON, _SUFFIX, _LEFT_VALUE):
        for match in pattern.finditer(text):
            operator = " ".join(match["operator"].casefold().split())
            operator = _EQUIVALENT.get(operator, operator)
            if pattern is _LEFT_VALUE:
                operator = _REVERSED[operator]
            result[(operator, match["number"], -1 if match["sign"] in {"-", "−"} else 1,
                    bool(match["percent"]))] += 1
    return result
