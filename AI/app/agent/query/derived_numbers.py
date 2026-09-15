"""인용한 원본 셀끼리 다시 계산해 답변의 수치를 검증한다.

두 값의 차이나 증감률은 셀에 그대로 적혀 있지 않다. 그렇다고 답변 전체를
버리면 맞는 답까지 막힌다. 답변이 계산에 쓴 두 값을 함께 밝힌 경우에만
같은 계산을 원본 값으로 재현해 대조한다. 모델의 계산을 믿는 것이 아니라
원본으로 다시 계산해 확인하는 것이다.

증감률은 답변에 먼저 적힌 값을 기준으로만 계산한다. 방향을 가리지 않으면
"6,101명에서 5,417명으로 12.63% 감소"처럼 기준을 뒤집은 값까지 통과한다.
"""
from decimal import Decimal, InvalidOperation
from itertools import combinations

from app.services.insights.verification.numeric_validation import (
    numbers,
    unmatched_numbers,
)

MAX_PAIRED_VALUES = 24


def derived_numbers(answer: str, evidence: list[object]) -> set[Decimal]:
    """답변이 함께 밝힌 두 셀 값의 차이를 모은다."""
    values = stated_cell_values(answer, evidence)
    return {abs(second - first) for first, second in combinations(values, 2)}


def derived_percent_numbers(answer: str, evidence: list[object]) -> set[Decimal]:
    """답변에 먼저 적힌 값을 기준으로 한 증감률만 모은다."""
    values = stated_cell_values(answer, evidence)
    return {
        abs((second - first) / first * 100)
        for first, second in combinations(values, 2)
        if first
    }


def stated_cell_values(answer: str, evidence: list[object]) -> list[Decimal]:
    """답변에 그대로 적힌 인용 셀 값을, 답변에 적힌 순서대로 돌려준다."""
    stated = numbers(answer)
    found: dict[Decimal, int] = {}
    for item in evidence:
        number = _decimal(getattr(item, "value", None))
        if number is None or number in found:
            continue
        position = _first_position(answer, number)
        if position is not None and not unmatched_numbers(str(number), stated):
            found[number] = position
    ordered = sorted(found, key=lambda value: found[value])
    return ordered[:MAX_PAIRED_VALUES]


def _first_position(answer: str, number: Decimal) -> int | None:
    """답변에서 그 값이 처음 적힌 위치. 천 단위 구분 기호도 함께 본다."""
    plain = str(number)
    positions = [answer.find(plain)]
    try:
        positions.append(answer.find(f"{int(number):,}"))
    except (ValueError, OverflowError):
        pass
    found = [position for position in positions if position >= 0]
    return min(found) if found else None


def _decimal(value: object) -> Decimal | None:
    if isinstance(value, bool) or not isinstance(value, (int, float, Decimal, str)):
        return None
    try:
        parsed = Decimal(str(value).replace(",", "").strip())
    except (InvalidOperation, ValueError):
        return None
    return parsed if parsed.is_finite() else None
