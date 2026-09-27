"""요청이 밝힌 계산을 현재 값에 직접 적용해 새 값이 맞는지 확인한다.

새 값이 요청에 그대로 적혀 있지 않아도 "10% 줄여줘"처럼 계산 방법을 밝혔다면
그 계산을 여기서 직접 해 보고 결과가 맞을 때만 허용한다. 계산은 LLM이 아니라
이 코드가 한다. "1081에서 1000으로"처럼 바꿀 값을 직접 밝힌 요청은 그대로
읽으면 되므로 계산을 추측하지 않는다.
"""
import re
from decimal import Decimal, ROUND_CEILING, ROUND_FLOOR, ROUND_HALF_UP

from app.agent.writeback.value_authorization import as_number, value_is_authorized

DIRECTION_WINDOW = 12
UP = ("올려", "올리", "인상", "증가", "늘려", "늘리", "상향", "더해", "더하", "추가",
      "increase", "raise", "up", "add")
DOWN = ("내려", "내리", "인하", "감소", "줄여", "줄이", "하향", "삭감", "빼", "차감",
        "decrease", "reduce", "cut", "down", "less")
PERCENT = re.compile(r"(?<![\w.])(\d+(?:\.\d+)?)\s*(?:%|퍼센트|프로|퍼)")
AMOUNT = re.compile(r"(?<![\w$.:%])(\d[\d,]*(?:\.\d+)?)\s*(?:명|개|원|건|점|시간|만큼)?")
# "두 배로", "3배로". 배정·배분 같은 낱말이 걸리지 않게 뒤 글자를 제한한다.
MULTIPLE = re.compile(r"(?<![\w.])(\d+(?:\.\d+)?|두|세|네|다섯|열)\s*배(?=로|만|$|[\s.,!?])")
KOREAN_MULTIPLE = {"두": 2, "세": 3, "네": 4, "다섯": 5, "열": 10}
HALF = ("절반", "반으로", "1/2")
# "1081명에서 1000명으로"처럼 바꾸기 전후 값을 직접 밝힌 요청.
TRANSITION = re.compile(
    r"\d[\d,]*(?:\.\d+)?\s*[가-힣]{0,3}\s*(?:에서|부터|->|→|~)\s*-?\d"
)


def _direction(instruction: str, end: int) -> int:
    """숫자 바로 뒤에 붙은 증감 표현. 멀리 떨어진 낱말은 보지 않는다."""
    tail = instruction[end : end + DIRECTION_WINDOW].casefold()
    if any(word in tail for word in DOWN):
        return -1
    return 1 if any(word in tail for word in UP) else 0


def _rounded(result: Decimal, current: Decimal) -> set[Decimal]:
    """원본 자릿수로 올림·내림·반올림한 값까지 같은 계산 결과로 본다.

    어느 쪽으로 반올림할지는 사람마다 다르므로 한 칸 범위를 열어 두되,
    설명 문장에는 반올림하지 않은 값을 그대로 적어 눈으로 확인하게 한다.
    """
    exponent = current.as_tuple().exponent
    places = -exponent if isinstance(exponent, int) and exponent < 0 else 0
    step = Decimal(1).scaleb(-places)
    modes = (ROUND_HALF_UP, ROUND_FLOOR, ROUND_CEILING)
    return {result, Decimal(1) * result, *(result.quantize(step, rounding=m) for m in modes)}


def _plain(value: Decimal) -> str:
    """0.90처럼 남는 자리를 떼고 지수 표기도 풀어서 적는다."""
    return f"{value.normalize():f}"


def _percent(instruction: str, current: Decimal, target: Decimal) -> str | None:
    for match in PERCENT.finditer(instruction):
        sign = _direction(instruction, match.end())
        if sign == 0:
            continue
        rate = Decimal(match.group(1)) / 100
        result = current * (1 + sign * rate)
        if target not in _rounded(result, current):
            continue
        word = "증가" if sign > 0 else "감소"
        return (
            f"요청한 {match.group(1)}% {word}를 현재 값 {_plain(current)}에 적용했습니다. "
            f"{_plain(current)} × {_plain(1 + sign * rate)} = {_plain(result)}"
        )
    return None


def _amount(instruction: str, current: Decimal, target: Decimal) -> str | None:
    for match in AMOUNT.finditer(instruction):
        sign = _direction(instruction, match.end())
        amount = as_number(match.group(1))
        if sign == 0 or amount is None or amount == 0:
            continue
        result = current + sign * amount
        if target not in _rounded(result, current):
            continue
        return (
            f"현재 값 {_plain(current)}에서 요청한 {_plain(amount)}만큼 "
            f"{'더했습니다' if sign > 0 else '뺐습니다'}. "
            f"{_plain(current)} {'+' if sign > 0 else '-'} {_plain(amount)} = {_plain(result)}"
        )
    return None


def _multiple(instruction: str, current: Decimal, target: Decimal) -> str | None:
    for match in MULTIPLE.finditer(instruction):
        size = Decimal(KOREAN_MULTIPLE.get(match.group(1), 0) or match.group(1))
        result = current * size
        if size > 0 and target in _rounded(result, current):
            return (
                f"현재 값 {_plain(current)}에 요청한 {_plain(size)}배를 적용했습니다. "
                f"{_plain(current)} × {_plain(size)} = {_plain(result)}"
            )
    if any(word in instruction for word in HALF):
        result = current / 2
        if target in _rounded(result, current):
            return (
                f"현재 값 {_plain(current)}의 절반입니다. "
                f"{_plain(current)} ÷ 2 = {_plain(result)}"
            )
    return None


def derived_value(current_value: object, new_value: object, instruction: str) -> str | None:
    """계산으로 설명되면 그 과정을 문장으로, 아니면 None."""
    current, target = as_number(current_value), as_number(new_value)
    if current is None or target is None or TRANSITION.search(instruction):
        return None
    return (
        _percent(instruction, current, target)
        or _multiple(instruction, current, target)
        or _amount(instruction, current, target)
    )


def authorize_value(current_value, new_value, instruction, formula) -> tuple:
    """(계산 과정, 거절 사유). 둘 다 None이면 요청에 값이 그대로 적혀 있다는 뜻이다."""
    if formula is not None or value_is_authorized(new_value, instruction):
        return None, None
    derivation = derived_value(current_value, new_value, instruction)
    if derivation is None:
        return None, "새 값이 요청에 적혀 있지도 않고 요청에서 계산 방법도 찾지 못했습니다."
    return derivation, None
