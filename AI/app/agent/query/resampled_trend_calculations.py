"""Exact calendar buckets retain original lineage and disclose incomplete periods."""
from collections import defaultdict
from dataclasses import dataclass, replace
from datetime import datetime, timedelta
from decimal import Decimal, localcontext
import re

from app.agent.query.excel_number_formats import parse_number_format
from app.agent.query.comparison_value_format import people_unit
from app.agent.query.trend_date_bounds import parse_trend_date_bounds

LABELS = {"month": "월별", "quarter": "분기별", "annual": "연도별"}
OPERATIONS = {"sum": "합계", "average": "관측값 단순평균", "min": "최솟값",
              "max": "최댓값", "last": "마지막 관측값"}
_NONADDITIVE = re.compile(r"인원|직원|재고|잔액|잔고|보유|자산|부채|주가|단가|가격|"
                         r"현금(?!\s*(?:흐름|유입|유출))|비중|비율|증감률|증가율|감소율|"
                         r"평균|주당|인당|%|\b(?:headcount|employees?|inventory|balances?|assets?|debt|prices?|"
                         r"ratio|share|percentage|rate|margin|average|eps|per)\b|"
                         r"\bcash\b(?!\s*(?:flows?|inflows?|outflows?|from|used)\b)", re.I)


@dataclass(frozen=True)
class ResampledBucket:
    label: str
    start: datetime
    end: datetime
    observations: tuple
    point: object
    complete: bool


def resample_candidate(candidate, units, request):
    points = candidate.observations
    if not points or len({(point.grain, point.scenario) for point in points}) != 1:
        raise ValueError("관측 주기·실적/예상 기준이 다른 값을 같은 기간으로 묶지 않았습니다.")
    if len({unit.identity for unit in units}) != 1:
        raise ValueError("서로 다른 원본 단위를 같은 기간으로 집계하지 않았습니다.")
    if any(parse_number_format(point.value.number_format).mode not in {"", "raw"} for point in points):
        raise ValueError("날짜·시간 표시 형식의 수치를 일반 금액이나 수량으로 집계하지 않았습니다.")
    source_grain = points[0].grain
    if source_grain is None and all(re.fullmatch(r"(?:FY\s*)?\d{4}", str(point.period_cell.value), re.I) for point in points):
        source_grain = "annual"
    rank = {None: 0, "month": 1, "quarter": 2, "annual": 3}
    if source_grain not in rank or rank[source_grain] > rank[request.grain]:
        raise ValueError("원본보다 더 세밀한 기간으로 임의 재집계하지 않았습니다.")
    if request.source_grain == "day" and source_grain is not None:
        raise ValueError("질문은 일별 원본을 지정했지만 원본은 다른 관측 주기입니다.")
    if any(any((point.period.hour, point.period.minute, point.period.second, point.period.microsecond)) for point in points):
        raise ValueError("시간대·하루 내 여러 관측값의 기준이 불명확하여 일별 기간 집계로 대신하지 않았습니다.")
    metric_label = re.sub(r"(?<=[a-z])(?=[A-Z])|[_/]", " ", str(points[0].label.value))
    if request.statistic == "sum" and (_NONADDITIVE.search(metric_label)
                                       or people_unit("", points[0].label.value)
                                       or any(people_unit("", unit.suffix) for unit in units)
                                       or any(parse_number_format(point.value.number_format).percent
                                              or people_unit("", parse_number_format(point.value.number_format).suffix)
                                              for point in points)):
        raise ValueError("인원·잔액 같은 시점 수치나 비율을 기간별로 더하지 않았습니다. 평균 또는 마지막 관측값을 지정해 주세요.")
    grouped = defaultdict(list)
    for point in points:
        start, end, label = bucket_bounds(point.period, request.grain)
        grouped[(start, end, label)].append(point)
    result = []
    for (start, end, label), items in sorted(grouped.items()):
        items = tuple(sorted(items, key=lambda point: point.period))
        if len({point.period for point in items}) != len(items):
            raise ValueError("동일 관측일의 중복 행을 기간 집계에 임의로 포함하지 않았습니다.")
        number = calculate_bucket(items, request.statistic)
        synthetic = replace(items[-1], period=start, grain=request.grain,
                            period_cell=replace(items[-1].period_cell, value=label),
                            value=replace(items[-1].value, value=number, formula=None))
        result.append(ResampledBucket(label, start, end, items, synthetic,
                                     complete_bucket(items, start, end, source_grain, request.statistic)))
    return tuple(result)


def calculate_bucket(points, statistic):
    values = [Decimal(str(point.value.value)) for point in points]
    if statistic == "last":
        return values[-1]
    if statistic in {"min", "max"}:
        return (min if statistic == "min" else max)(values)
    if statistic not in {"sum", "average"}:
        raise ValueError("요청한 기간 집계 연산이 명확하지 않습니다.")
    with localcontext() as context:
        context.prec = max(60, max(value.adjusted() for value in values)
                           - min(value.as_tuple().exponent for value in values) + len(str(len(values))) + 16)
        return sum(values) / (len(values) if statistic == "average" else 1)


def bucket_bounds(date, grain):
    month = {"month": date.month, "quarter": (date.month - 1) // 3 * 3 + 1, "annual": 1}[grain]
    start = datetime(date.year, month, 1)
    span = {"month": 1, "quarter": 3, "annual": 12}[grain]
    next_month = date.year * 12 + month - 1 + span
    end = datetime(next_month // 12, next_month % 12 + 1, 1) - timedelta(days=1)
    label = {"month": f"{date.year}년 {month}월", "quarter": f"{date.year}년 {(month - 1) // 3 + 1}분기",
             "annual": f"{date.year}년"}[grain]
    return start, end, label


def complete_bucket(points, start, end, source_grain, statistic):
    if statistic == "last":
        return points[-1].period == end
    if source_grain in {"month", "quarter", "annual"}:
        step = {"month": 1, "quarter": 3, "annual": 12}[source_grain]
        expected = set(range(start.year * 12 + start.month, end.year * 12 + end.month + 1, step))
        actual = [point.period.year * 12 + point.period.month for point in points]
        return len(actual) == len(set(actual)) and set(actual) == expected
    actual = {point.period.date() for point in points}
    return len(actual) == (end - start).days + 1 and min(actual) == start.date() and max(actual) == end.date()


def missing_bucket_scope(buckets, request, residual, observations, named):
    bounds, error = parse_trend_date_bounds(residual, observations, named)
    if error:
        raise ValueError(error)
    if any(bucket_bounds(left.end + timedelta(days=1), request.grain)[0] != right.start
           for left, right in zip(buckets, buckets[1:])):
        return True
    return bool(bounds.start and bucket_bounds(bounds.start, request.grain)[0] < buckets[0].start
                or bounds.end and bucket_bounds(bounds.end, request.grain)[0] > buckets[-1].start)
