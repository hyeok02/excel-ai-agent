"""Exact temporal ranking; the requested basis never silently changes."""
from dataclasses import dataclass
from decimal import Decimal
from fractions import Fraction

from app.agent.query.excel_number_formats import parse_number_format
from app.agent.query.trend_calculations import change_percent, decimal_value, exact_difference


@dataclass(frozen=True)
class RankedChange:
    candidate: object
    units: tuple
    start: int
    end: int
    difference: Decimal
    score: Decimal
    ordering: Fraction


@dataclass(frozen=True)
class ChangeRanking:
    metrics: tuple[RankedChange, ...]
    winners: tuple[RankedChange, ...]
    basis: str


def calculate_ranking(series, request, basis=None):
    basis = basis or ("max_drawdown" if request.basis == "auto" else request.basis)
    if basis not in {"net", "extreme_to_latest", "max_drawdown", "adjacent"}:
        raise ValueError("비교 기준을 확정하지 못했습니다.")
    if request.direction not in {"increase", "decrease"} or not series:
        raise ValueError("비교할 대상과 증감 방향이 필요합니다.")
    reference_dates, reference_units, metrics = None, None, []
    for candidate, units in series:
        points = candidate.observations
        dates = tuple(point.period for point in points)
        identities = {unit.identity for unit in units}
        if (candidate.error or len(points) < 2 or len(units) != len(points)
                or tuple(sorted(set(dates))) != dates or len(identities) != 1):
            raise ValueError("대상별 전체 날짜·값·단위를 연결하지 못했습니다.")
        if any(parse_number_format(point.value.number_format).mode not in {"", "raw"} for point in points):
            raise ValueError("비교 수치의 표시 형식을 확정하지 못했습니다.")
        if reference_dates is not None and (dates != reference_dates or identities != reference_units):
            raise ValueError("비교 대상의 기간 또는 단위가 서로 다릅니다.")
        reference_dates, reference_units = dates, identities
        values = tuple(decimal_value(point.value.value) for point in points)
        if request.percent and basis in {"max_drawdown", "adjacent"} and any(value <= 0 for value in values[:-1]):
            raise ValueError("비교 기준값이 0 이하인 대상이 있어 증감률 순위를 확정하지 않았습니다.")
        pairs = _pairs(values, request.direction, basis, request.percent)
        best = None
        for start, end in pairs:
            difference = exact_difference(values[start], values[end])
            amount = change_percent(values[start], values[end]) if request.percent else difference
            if amount is None:
                raise ValueError("비교 기준값이 0 이하인 대상이 있어 증감률 순위를 확정하지 않았습니다.")
            score = amount if request.direction == "increase" else amount.copy_negate()
            exact = Fraction(difference) / Fraction(values[start]) * 100 if request.percent else Fraction(difference)
            ordering = exact if request.direction == "increase" else -exact
            item = RankedChange(candidate, tuple(units), start, end, difference, score, ordering)
            if best is None or item.ordering > best.ordering:
                best = item
        metrics.append(best)
    maximum = max(item.ordering for item in metrics)
    winners = tuple(item for item in metrics if item.ordering == maximum) if maximum > 0 else ()
    return ChangeRanking(tuple(metrics), winners, basis)


def _pairs(values, direction, basis, percent=False):
    end = len(values) - 1
    if basis == "net":
        return ((0, end),)
    if basis == "extreme_to_latest":
        extreme = max(values[:-1]) if direction == "decrease" else min(values[:-1])
        return ((values.index(extreme), end),)
    if basis == "adjacent":
        return ((index - 1, index) for index in range(1, len(values)))
    return _chronological_pairs(values, direction, percent)


def _chronological_pairs(values, direction, percent):
    # An extremum must precede its endpoint; never compare a later high to an
    # earlier low. Equal interval scores retain the earliest witness pair.
    low = high = 0
    for end in range(1, len(values)):
        yield (high if direction == "decrease" else low), end
        if percent and low != high:
            # Crossing below zero can make a smaller positive baseline have
            # the largest percentage decline, unlike absolute drawdown.
            yield (low if direction == "decrease" else high), end
        if values[end] < values[low]:
            low = end
        if values[end] > values[high]:
            high = end
