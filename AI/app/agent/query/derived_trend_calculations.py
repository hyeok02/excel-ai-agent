"""Exact derived observations with both original operands retained as lineage."""
from dataclasses import dataclass
from calendar import monthrange
from decimal import localcontext

from app.agent.query.trend_calculations import decimal_value, exact_difference
from app.agent.query.trend_date_bounds import select_trend_periods
from app.agent.query.derived_trend_sources import shift_month


@dataclass(frozen=True)
class DerivedPoint:
    current: object
    base: object
    value: object


def growth_points(candidate, bounds, basis, decrease=False):
    points = candidate.observations
    selected = select_trend_periods(points, bounds)
    by_date = {point.period: point for point in points}
    previous = {right.period: left for left, right in zip(points, points[1:])}
    output, skipped = [], []
    for point in selected:
        if basis == "previous":
            base = previous.get(point.period)
        else:
            target = shift_month(point.period, -12 if basis == "year" else -1)
            if point.period.day != monthrange(point.period.year, point.period.month)[1] and target.day != point.period.day:
                raise ValueError("전월·전년 같은 날짜가 존재하지 않습니다. 가까운 날짜를 비교 기준으로 대신하지 않았습니다.")
            base = by_date.get(target)
        if base is None:
            # A source's initial baseline-only prefix is disclosed, never
            # confused with a missing comparison inside an explicit window.
            if bounds.start is None and not output:
                skipped.append(point)
                continue
            raise ValueError("요청 기간의 전년 동기·전월 또는 이전 관측 기준값이 없습니다. 가까운 날짜로 대신하지 않았습니다.")
        current, denominator = decimal_value(point.value.value), decimal_value(base.value.value)
        if denominator <= 0:
            raise ValueError("증감률의 기준값이 0 이하인 시점이 있어 전체 증감률 추이를 계산하지 않았습니다.")
        numerator = exact_difference(denominator, current)
        if decrease:
            numerator = numerator.copy_negate()
        output.append(DerivedPoint(point, base, _ratio(numerator, denominator)))
    if len(output) < 2:
        raise ValueError("추이를 설명할 수 있는 파생 관측값이 두 개 이상 필요합니다. 비교 기준 기간을 포함한 원본을 확인해 주세요.")
    return tuple(output), tuple(skipped)


def share_points(numerator, denominator, *, component=False):
    if tuple(point.period for point in numerator.observations) != tuple(point.period for point in denominator.observations):
        raise ValueError("분자와 분모의 날짜가 일치하지 않습니다. 겹치는 일부 날짜만으로 전체 비중을 대신하지 않았습니다.")
    output = []
    for current, base in zip(numerator.observations, denominator.observations):
        top, bottom = decimal_value(current.value.value), decimal_value(base.value.value)
        if bottom <= 0:
            raise ValueError("분모가 0 이하인 시점이 있어 전체 비중·비율 추이를 계산하지 않았습니다.")
        if top < 0:
            raise ValueError("분자가 음수인 시점의 비중을 일반적인 구성비로 해석하지 않았습니다. 원본 지표를 확인해 주세요.")
        if component and top > bottom:
            raise ValueError("부분의 값이 전체보다 큰 시점이 있어 이를 구성비로 검증하지 않았습니다. 분자·분모의 범위를 확인해 주세요.")
        output.append(DerivedPoint(current, base, _ratio(top, bottom)))
    return tuple(output)


def _ratio(top, bottom):
    with localcontext() as context:
        context.prec = max(40, len(top.as_tuple().digits) + len(bottom.as_tuple().digits) + 16)
        result = top / bottom
    if not result.is_finite():
        raise ValueError("파생 계산 결과가 유한한 숫자가 아닙니다.")
    return result
