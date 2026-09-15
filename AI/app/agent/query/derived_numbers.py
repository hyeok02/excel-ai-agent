"""인용한 원본 셀끼리 다시 계산해 답변의 수치를 검증한다.

두 값의 차이나 증감률은 셀에 그대로 적혀 있지 않다. 그렇다고 답변 전체를
버리면 맞는 답까지 막힌다. 답변이 계산에 쓴 두 값을 함께 밝힌 경우에만
같은 계산을 원본 값으로 재현해 대조한다. 모델의 계산을 믿는 것이 아니라
원본으로 다시 계산해 확인하는 것이다.

증감률은 먼저 적힌 값을 기준으로만 계산한다. 방향을 가리지 않으면
"6,101명에서 5,417명으로 12.63% 감소"처럼 기준을 뒤집은 값까지 통과한다.

비중(a가 b의 몇 %인가)은 증감을 말하지 않는 문장에서만 인정한다. 증감
문장에서까지 허용하면 "6,101명에서 5,417명으로 88.79% 감소"가 통과한다.
"""
from decimal import Decimal, InvalidOperation
from itertools import combinations, permutations

from app.agent.query.answer_clauses import stated_direction
from app.services.insights.verification.numeric_validation import (
    numbers,
    unmatched_numbers,
)

MAX_PAIRED_VALUES = 24


def derived_numbers(text: str, evidence: list[object]) -> set[Decimal]:
    """함께 밝힌 두 셀 값의 차이를 모은다."""
    values = stated_cell_values(text, evidence)
    return {abs(second - first) for first, second in combinations(values, 2)}


def derived_percent_numbers(text: str, evidence: list[object]) -> set[Decimal]:
    """먼저 적힌 값을 기준으로 한 증감률과, 증감 문장이 아닐 때의 비중을 모은다."""
    values = stated_cell_values(text, evidence)
    rates = {
        abs((second - first) / first * 100)
        for first, second in combinations(values, 2)
        if first
    }
    if stated_direction(text) is not None:
        return rates
    ratios = {
        abs(second / first * 100) for first, second in permutations(values, 2) if first
    }
    return rates | ratios


def stated_cell_values(text: str, evidence: list[object]) -> list[Decimal]:
    """문장에 그대로 적힌 인용 셀 값을, 적힌 순서대로 돌려준다."""
    stated = numbers(text)
    found: dict[Decimal, int] = {}
    for item in evidence:
        number = _decimal(getattr(item, "value", None))
        if number is None or number in found:
            continue
        position = _first_position(text, number)
        if position is not None and not unmatched_numbers(str(number), stated):
            found[number] = position
    ordered = sorted(found, key=lambda value: found[value])
    return ordered[:MAX_PAIRED_VALUES]


def _first_position(text: str, number: Decimal) -> int | None:
    """그 값이 처음 적힌 위치. 천 단위 구분 기호도 함께 본다."""
    plain = str(number)
    positions = [text.find(plain)]
    try:
        positions.append(text.find(f"{int(number):,}"))
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
