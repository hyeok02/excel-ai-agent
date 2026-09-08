import re
from datetime import date

from app.services.insights.verification.numeric_validation import numbers


def value_is_authorized(value: object, instruction: str) -> bool:
    normalized = instruction.casefold()
    if value is None:
        return bool(re.search(r"비우|삭제|지우|제거|clear|delete|remove", normalized))
    if isinstance(value, bool):
        labels = ("true", "참", "예") if value else ("false", "거짓", "아니오")
        return any(label in normalized for label in labels)
    if isinstance(value, (int, float)):
        return bool(numbers(str(value)) & numbers(instruction))
    text = str(value).strip().casefold()
    if text and text in normalized:
        return True
    return _iso_date(text) and numbers(text) <= numbers(instruction)


def _iso_date(value: str) -> bool:
    try:
        date.fromisoformat(value)
        return True
    except ValueError:
        return False
