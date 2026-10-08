import re
from datetime import date
from decimal import Decimal, InvalidOperation

from app.agent.writeback.change_direction import direction_after
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
        return bool(numbers(str(value)) & _stated_numbers(instruction))
    text = str(value).strip().casefold()
    if text and text in normalized:
        return True
    return _iso_date(text) and numbers(text) <= numbers(instruction)


AMOUNT_TOKEN = re.compile(r"(?<![\w$.:])-?\d[\d,]*(?:\.\d+)?\s*(?:백만|조|억|만(?!큼)|천)?")


def _stated_numbers(instruction: str) -> set:
    """
    "1억 줄여줘"의 1억은 바꿀 값이 아니라 뺄 양이다.

    그 숫자를 목표값으로 받아 주면, 5억을 1억으로 덮어쓰는 변경안이 "요청에
    적힌 값"이라는 이유로 승인 화면에 오른다. 앞뒤 값을 함께 밝힌 요청의
    바꿀 값(1081에서 1000으로)은 증감 표현이 뒤따라도 그대로 둔다.
    """
    stated = [match.span("next") for match in VALUE_TRANSITION.finditer(instruction)]
    deltas = set()
    for match in AMOUNT_TOKEN.finditer(instruction):
        if any(low <= match.start() < high for low, high in stated):
            continue
        if direction_after(instruction, match.end()):
            deltas |= numbers(match.group())
    return numbers(instruction) - deltas


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
