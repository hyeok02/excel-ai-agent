import re
from datetime import date
from decimal import Decimal, InvalidOperation

from app.services.insights.verification.numeric_validation import numbers

# "1081에서 981로", "1,081 → 981", "from 1081 to 981"처럼
# 바꾸기 전 값과 바꿀 값을 함께 적은 표현.
# 앞에 문자가 붙은 숫자(B20 같은 셀 주소)는 값으로 보지 않는다.
VALUE_TRANSITION = re.compile(
    r"(?<![\w$.:])(?P<current>-?\d[\d,]*(?:\.\d+)?)\s*"
    r"(?:에서|부터|을|를|는|은|->|→|~|\bto\b)\s*"
    r"(?<![\w$.:])(?P<next>-?\d[\d,]*(?:\.\d+)?)"
)


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


def as_number(value: object) -> Decimal | None:
    if value is None or isinstance(value, bool):
        return None
    text = str(value).strip().replace(",", "")
    if not text:
        return None
    try:
        return Decimal(text)
    except InvalidOperation:
        return None


def stated_current_value(instruction: str, new_value: object) -> Decimal | None:
    """
    요청이 바꾸기 전 값을 함께 밝혔다면 그 값을 돌려준다.

    밝히지 않았으면 None이며, 이때는 기존 값을 검사하지 않는다.
    사용자가 값을 밝혔는데 대상 셀이 다른 값을 들고 있다면 엉뚱한 셀을 고른 것이므로,
    검증기가 그 변경안을 걸러낼 수 있도록 기준값을 넘겨준다.
    """
    target = as_number(new_value)
    if target is None:
        return None
    for match in VALUE_TRANSITION.finditer(instruction):
        if as_number(match.group("next")) == target:
            return as_number(match.group("current"))
    return None
