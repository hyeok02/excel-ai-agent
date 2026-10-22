"""Recognize scalar display syntax while preserving signed/accounting values."""
from decimal import Decimal, InvalidOperation
import re

DISPLAY = re.compile(
    r"^\s*(?P<open>\()?\s*(?:[$€£₩¥₹]|USD|EUR|KRW|JPY|GBP)?\s*"
    r"(?P<number>[+\-−]?\d[\d,]*(?:\.\d+)?(?:[eE][+\-]?\d+)?)\s*"
    r"(?P<unit>[%％]|[A-Za-z]{1,12}|(?:백만|십억|천만|만|천|억|조)?"
    r"(?:원|명|개|건|대|회|주|곳|점|시간|분|초|톤|킬로그램|미터)?)?\s*(?P<close>\))?\s*$", re.I,
)


def scalar(value):
    if value is None or isinstance(value, bool):
        return False
    if isinstance(value, (int, float, Decimal)):
        try:
            return Decimal(str(value)).is_finite()
        except InvalidOperation:
            return False
    match = DISPLAY.fullmatch(str(value))
    return bool(match and bool(match.group("open")) == bool(match.group("close")))


def negative(value):
    match = DISPLAY.fullmatch(str(value))
    if match:
        return bool(match.group("open")) or match.group("number").startswith(("-", "−"))
    return str(value).lstrip().startswith(("-", "−"))
