"""Read a complete filtered population before deriving scoped trajectories."""
from dataclasses import replace
import re

from app.agent.query.grouped_trend_scope import filter_records
from app.agent.query.grouped_tabular_state import typed_key
from app.agent.query.metric_observation_cells import MetricObservation
from app.agent.query.metric_observation_periods import source_period
from app.agent.query.tabular_catalog import build_query_tables
from app.agent.query.trend_date_bounds import parse_trend_date_bounds
from app.agent.query.trend_source_readback import table_rows, column_cells
from app.agent.query.derived_trend_sources import shift_month


def complete_records(source, summary, index):
    if source.hidden:
        raise ValueError("숨겨진 행이 있어 조건·그룹 파생 계산의 전체 모집단을 확인하지 못했습니다.")
    if summary is None:
        return list(source.records)
    rows, error = table_rows(source.table, build_query_tables(summary), index, source.request.residual)
    if error:
        raise ValueError("계산에 사용할 원본 표 전체를 다시 확인하지 못했습니다.")
    header = max(int(re.search(r"\d+$", cell.address)[0]) for cell in source.headers.values())
    return [column_cells(row) for row in rows if row.row_number > header and row.cells]


def dated_population(source, records, named):
    categorical = tuple(item for item in source.request.filters if isinstance(item.value, str))
    numeric = tuple(item for item in source.request.filters if not isinstance(item.value, str))
    records = filter_records(records, categorical, source.table)
    label = source.headers[source.metric.id]
    points = []
    for row in records:
        date = row.get(source.date.id)
        period = source_period(date.value) if date else None
        if period is None:
            raise ValueError("선택한 모집단에 날짜를 알 수 없는 행이 있습니다.")
        points.append(MetricObservation(label, label, period, date, None, None, (), ()))
    bounds, error = parse_trend_date_bounds(source.request.residual, points, (*named, source.table.sheet_name))
    if error:
        raise ValueError(error)
    if bounds.relative and numeric:
        accepted = {id(row) for row in filter_records(records, numeric, source.table)}
        paired = [(row, point) for row, point in zip(records, points) if id(row) in accepted]
        records, points = [row for row, _ in paired], [point for _, point in paired]
        bounds, error = parse_trend_date_bounds(source.request.residual, points, (*named, source.table.sheet_name))
        if error:
            raise ValueError(error)
    return records, points, bounds


def expanded_growth_source(source, basis, named, index, summary):
    records, points, bounds = dated_population(source, complete_records(source, summary, index), named)
    def key(row):
        cells = [row.get(group) for group in source.request.groups]
        if any(cell is None or typed_key(cell.value, cell.number_format) is None for cell in cells):
            raise ValueError("원본 그룹의 자료형·표시 형식을 확정하지 못했습니다.")
        return tuple(typed_key(cell.value, cell.number_format)[0] for cell in cells)
    current = [row for row, point in zip(records, points)
               if (bounds.start is None or point.period >= bounds.start)
               and (bounds.end is None or point.period <= bounds.end)]
    accepted = filter_records(current, source.request.filters, source.table)
    active = {key(row) for row in accepted}
    start, end = bounds.start, bounds.end
    calendar_baseline = bool(start and basis in {"year", "month"})
    current_ids = {id(row) for row in accepted}
    required = {(key(row), shift_month(point.period, -12 if basis == "year" else -1))
                for row, point in zip(records, points) if id(row) in current_ids} if calendar_baseline else set()
    needed_dates = {period for _, period in required}
    paired = [(row, point) for row, point in zip(records, points)
              if not calendar_baseline
              or id(row) in current_ids or point.period in needed_dates]
    paired = [(row, point) for row, point in paired if key(row) in active]
    records, points = [row for row, _ in paired], [point for _, point in paired]
    if calendar_baseline:
        # Calendar growth needs exact group/date operands, not every row in a
        # continuous interval between last year's baseline and this period.
        selected = [row for row, point in zip(records, points)
                    if id(row) in current_ids or (key(row), point.period) in required]
    elif start and basis == "previous":
        priors, prior_rows = {}, []
        for moment in sorted({point.period for point in points if point.period < start}, reverse=True):
            candidates = [row for row, point in zip(records, points) if point.period == moment and key(row) not in priors]
            accepted = filter_records(candidates, source.request.filters, source.table)
            prior_rows.extend(accepted)
            priors.update({key(row): moment for row in accepted})
            if len(priors) == len(active):
                break
        selected = [row for row, point in zip(records, points) if point.period >= start
                    and (end is None or point.period <= end)] + prior_rows
    else:
        selected = [row for row, point in zip(records, points)
                    if (start is None or point.period >= start) and (end is None or point.period <= end)]
    if not selected:
        raise ValueError("조건과 조회 기간에 맞는 원본 값이 없습니다.")
    selected = filter_records(selected, source.request.filters, source.table)
    return replace(source, records=tuple(selected), note=bounds.note), bounds
