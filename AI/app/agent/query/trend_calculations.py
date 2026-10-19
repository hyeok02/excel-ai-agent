"""Exact, chronological movements for one fully bound source series."""
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation, localcontext


@dataclass(frozen=True)
class TrendRun:
    start: int
    end: int
    direction: int
    reversal: bool


@dataclass(frozen=True)
class TrendProfile:
    observations: tuple
    values: tuple[Decimal, ...]
    runs: tuple[TrendRun, ...]
    minimum: tuple[int, ...]
    maximum: tuple[int, ...]
    rising: int
    falling: int
    flat: int


def decimal_value(value):
    if isinstance(value, bool) or value is None:
        raise ValueError("추이에는 유한한 숫자가 필요합니다.")
    try:
        number = Decimal(str(value))
    except (InvalidOperation, ValueError) as exc:
        raise ValueError("추이에는 유한한 숫자가 필요합니다.") from exc
    if not number.is_finite():
        raise ValueError("추이에는 유한한 숫자가 필요합니다.")
    return number


def exact_difference(before, after):
    """A tiny change next to a huge baseline must not round to no movement."""
    with localcontext() as context:
        context.prec = _precision(before, after)
        return after - before


def display_scale(value, multiplier, divisor):
    with localcontext() as context:
        context.prec = _precision(value, Decimal(multiplier), Decimal(divisor))
        return value * Decimal(multiplier) / Decimal(divisor)


def change_percent(before, after):
    if before <= 0:
        return None
    difference = exact_difference(before, after)
    with localcontext() as context:
        context.prec = max(32, _precision(before, after))
        return difference / before * 100


def _precision(*values):
    return max(32, max(value.adjusted() for value in values)
               - min(value.as_tuple().exponent for value in values) + 16)


def calculate_trend(observations):
    items = tuple(sorted(observations, key=lambda item: item.period))
    if len(items) < 2 or len({item.period for item in items}) != len(items):
        raise ValueError("추이는 서로 다른 날짜의 관측값이 두 개 이상 필요합니다.")
    values = tuple(decimal_value(item.value.value) for item in items)
    directions = [(right > left) - (right < left) for left, right in zip(values, values[1:])]
    runs, start, previous = [], 0, 0
    for end in range(1, len(directions) + 1):
        direction = directions[start]
        if end != len(directions) and directions[end] == direction:
            continue
        reversal = bool(direction and previous and direction != previous)
        runs.append(TrendRun(start, end, direction, reversal))
        if direction:
            previous = direction
        start = end
    low, high = min(values), max(values)
    return TrendProfile(
        items, values, tuple(runs),
        tuple(index for index, value in enumerate(values) if value == low),
        tuple(index for index, value in enumerate(values) if value == high),
        directions.count(1), directions.count(-1), directions.count(0),
    )
