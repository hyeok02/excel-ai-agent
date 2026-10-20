"""Aggregate only explicitly requested, date-aligned source populations."""
from collections import defaultdict
from dataclasses import replace
from decimal import Decimal, localcontext

from app.agent.query.grouped_tabular_state import typed_key
from app.agent.query.metric_observation_cells import MetricObservation, _numeric
from app.agent.query.metric_observation_periods import source_period
from app.agent.query.trend_period_metadata import trend_period_metadata
from app.agent.query.trend_row_metadata import row_unit_context, row_scenario
from app.agent.query.metric_observation_units import observation_unit
from app.agent.query.trend_source_models import TrendCandidate, MAX_TREND_OBSERVATIONS
from app.agent.query.trend_source_vertical import _IDENTITY
from app.agent.query.trend_selection import prepare_trend_candidate


def grouped_series(source, index):
    identity = _identities(source, source.records)
    groups = defaultdict(list)
    for row in source.records:
        parts = []
        for key in source.request.groups:
            cell = row.get(key)
            if cell is None or cell.value in (None, ""):
                raise ValueError("그룹을 구분하는 원본 값이 누락되어 전체 그룹 추이를 확정하지 못했습니다.")
            part = typed_key(cell.value, cell.number_format)
            if part is None:
                raise ValueError("원본 그룹 값의 자료형이나 표시 단위를 확정하지 못했습니다.")
            parts.append(part[0])
        groups[tuple(parts)].append(row)
    if len(groups) > 20 or len(source.records) > MAX_TREND_OBSERVATIONS:
        raise ValueError("전체 그룹·시계열 검증 한도를 넘었습니다. 조건이나 기간을 좁혀 주세요.")
    result = []
    for records in groups.values():
        title = ", ".join(f"{source.headers[key].value}: {records[0][key].value}" for key in source.request.groups)
        dates, references = defaultdict(list), [*source.headers.values(), *source.context]
        for row in records:
            value, date = row.get(source.metric.id), row.get(source.date.id)
            if value is None or not _numeric(value.value) or date is None or source_period(date.value) is None:
                raise ValueError("선택한 그룹·기간에 숫자 또는 저장된 수식 결과가 없습니다. 누락을 0으로 바꾸지 않았습니다.")
            entities = tuple([row[key] for key in source.request.groups] + list(identity))
            grain, scenario = trend_period_metadata(date.value)
            point = MetricObservation(source.headers[source.metric.id], value, source_period(date.value), date,
                                      grain, row_scenario(source.headers, row, scenario), (source.headers[source.date.id],),
                                      (*entities, *source.context), row_unit_context(source.headers, row))
            dates[point.period].append(point)
            references.extend((value, date, *entities, *observation_unit(point, index.rows).references))
            references.extend(row[condition.column_id] for condition in source.request.filters)
        points = tuple(_aggregate(items, source.request.statistic, index.rows) for _, items in sorted(dates.items()))
        candidate, units = prepare_trend_candidate(TrendCandidate(source.table.id, points, source.context,
                                                  hidden_rows=source.hidden, period_note=source.note), index.rows)
        if candidate.error:
            raise ValueError("요청한 그룹의 전체 시계열을 확정하지 못했습니다: " + candidate.error)
        result.append((title, candidate, units, tuple(dict.fromkeys(references))))
    return result


def _identities(source, records):
    ignored = {source.metric.id, source.date.id, *source.request.groups}
    identities = []
    for column in source.table.columns:
        if column.id in ignored:
            continue
        values = [row.get(column.id) for row in records]
        is_identity = _IDENTITY.search(column.header) or any(
            cell and isinstance(cell.value, str) and cell.value.strip() for cell in values)
        if not is_identity:
            continue
        if any(cell is None or cell.value in (None, "") for cell in values):
            raise ValueError("추이의 회사·시나리오 등 대상 구분값에 누락이 있습니다.")
        if len({(type(cell.value).__name__, cell.value) for cell in values}) != 1:
            raise ValueError("선택하지 않은 회사·시나리오·지역 등의 구분값이 서로 다릅니다. 그룹이나 조건을 더 지정해 주세요.")
        identities.append(values[0])
    return tuple(identities)


def _aggregate(points, statistic, rows):
    if len(points) > 1 and statistic is None:
        raise ValueError("같은 그룹·날짜에 여러 행이 있습니다. 합계·평균 등 계산 방식을 지정해 주세요. 임의 합산하거나 중복 제거하지 않았습니다.")
    if statistic is None:
        return points[0]
    if len({(point.grain, point.scenario) for point in points}) != 1:
        raise ValueError("같은 날짜의 값이라도 관측 주기·실적/예상 구분이 달라 합산하지 않았습니다.")
    units = [observation_unit(point, rows) for point in points]
    if len({unit.identity for unit in units}) != 1 or any(unit.identity[:1] == ("conflicting_units",) for unit in units):
        raise ValueError("동일 그룹·날짜에 단위가 다른 값이 섞여 있어 합산하지 않았습니다.")
    values = [Decimal(str(point.value.value)) for point in points]
    with localcontext() as context:
        context.prec = max(60, max(value.adjusted() for value in values)
                           - min(value.as_tuple().exponent for value in values) + len(str(len(values))) + 16)
        if statistic in {"sum", "average"}:
            value = sum(values) / (len(values) if statistic == "average" else 1)
        elif statistic in {"min", "max"}:
            value = (min if statistic == "min" else max)(values)
        else:
            raise ValueError("요청한 집계 방식을 확정하지 못했습니다.")
    # A calculated cell is used only for rendering; evidence always retains the
    # original contributing cells and never this synthetic value/address pair.
    calculated = replace(points[0].value, value=value, formula=None)
    return replace(points[0], value=calculated)
