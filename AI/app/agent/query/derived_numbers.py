"""인용한 원본 셀끼리 다시 계산해 답변의 수치를 검증한다.

두 값의 차이나 증감률은 셀에 그대로 적혀 있지 않다. 그렇다고 답변 전체를
버리면 맞는 답까지 막힌다. 답변이 계산에 쓴 두 값을 함께 밝힌 경우에만
같은 계산을 원본 값으로 재현해 대조한다. 모델의 계산을 믿는 것이 아니라
원본으로 다시 계산해 확인하는 것이다.
"""
from decimal import Decimal, InvalidOperation
from itertools import combinations, permutations

from app.services.insights.verification.numeric_validation import (
    numbers,
    unmatched_numbers,
)

MAX_PAIRED_VALUES = 24


def derived_numbers(answer: str, evidence: list[object]) -> set[Decimal]:
    """답변이 함께 밝힌 두 셀 값의 차이를 모두 모은다."""
    values = stated_cell_values(answer, evidence)
    return {abs(second - first) for first, second in combinations(values, 2)}


def derived_percent_numbers(answer: str, evidence: list[object]) -> set[Decimal]:
    """답변이 함께 밝힌 두 셀 값으로 만들 수 있는 증감률과 비중을 모은다."""
    values = stated_cell_values(answer, evidence)
    results = set()
    for first, second in permutations(values, 2):
        if not first:
            continue
        results.add(abs((second - first) / first * 100))
        results.add(abs(second / first * 100))
    return results


def stated_cell_values(answer: str, evidence: list[object]) -> list[Decimal]:
    """답변에 그대로 적힌 인용 셀 값만 계산 재료로 쓴다."""
    stated = numbers(answer)
    values: list[Decimal] = []
    for item in evidence:
        number = _decimal(getattr(item, "value", None))
        if number is None or number in values:
            continue
        if not unmatched_numbers(str(number), stated):
            values.append(number)
        if len(values) >= MAX_PAIRED_VALUES:
            break
    return values


def _decimal(value: object) -> Decimal | None:
    if isinstance(value, bool) or not isinstance(value, (int, float, Decimal, str)):
        return None
    try:
        parsed = Decimal(str(value).replace(",", "").strip())
    except (InvalidOperation, ValueError):
        return None
    return parsed if parsed.is_finite() else None
