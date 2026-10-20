"""Resolve categorical population and calendar bounds before numeric predicates."""
from app.agent.query.metric_observation_cells import MetricObservation
from app.agent.query.metric_observation_periods import source_period
from app.agent.query.tabular_filters import matches
from app.agent.query.trend_date_bounds import parse_trend_date_bounds, select_trend_periods
from app.agent.query.trend_source_scope import scope_dated_items


def scoped_records(records, request, table, label, date_id, names):
    categorical = tuple(item for item in request.filters if isinstance(item.value, str))
    numeric = tuple(item for item in request.filters if not isinstance(item.value, str))
    records = filter_records(records, categorical, table)
    context = tuple(cell for row in records for key, cell in row.items() if key != date_id and cell != label)
    points = []
    for row in records:
        cell = row.get(date_id)
        if cell is None or (period := source_period(cell.value)) is None:
            raise ValueError("날짜를 알 수 없는 행이 있어 요청 기간 밖이라고 가정하지 않았습니다.")
        points.append(MetricObservation(label, label, period, cell, None, None, (), context))
    bounds, error = parse_trend_date_bounds(request.residual, points, (label.sheet_name, *names))
    if error:
        return (), "", error
    if bounds.relative:
        selected = filter_records(records, numeric, table)
        # Relative anchors belong to the final requested population, not an
        # excluded branch/department or a row rejected by the numeric condition.
        return scope_dated_items(request.residual, label, [(row, row.get(date_id)) for row in selected],
                                 context, source_names=names)
    selected = {id(point) for point in select_trend_periods(points, bounds)}
    records = [row for row, point in zip(records, points) if id(point) in selected]
    return tuple(filter_records(records, numeric, table)), bounds.note, None


def filter_records(records, filters, table):
    columns = {column.id: column for column in table.columns}
    selected = []
    for row in records:
        outcomes = []
        for condition in filters:
            cell = row.get(condition.column_id)
            if cell is None or cell.value in (None, ""):
                outcomes.append(None)
            else:
                outcomes.append(matches(cell.value, condition, cell.number_format, columns[condition.column_id].header))
        if False in outcomes:
            continue
        if None in outcomes:
            raise ValueError("조건에 사용할 값이 비어 있거나 계산되지 않아 대상 행을 확정하지 못했습니다.")
        selected.append(row)
    return selected
