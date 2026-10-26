"""Bind a horizontal metric label to its own period-axis category header."""
from app.agent.query.metric_observation_cells import _column, _human_label, _numeric
from app.agent.query.metric_observation_periods import source_period
from app.agent.query.metric_semantics import column_metric_conflict
from app.agent.query.tabular_catalog_models import QueryColumn


def row_metric_column(label, axis, rows):
    left = min((_column(cell) for cell in axis.cells), default=_column(label))
    context = []
    for row in rows:
        if not 0 <= axis.row_number - row.row_number <= 3:
            continue
        candidates = [cell for cell in row.cells
                      if left <= _column(cell) <= _column(label)
                      and isinstance(cell.value, str) and cell.value.strip()]
        if candidates:
            cell = max(candidates, key=_column)
            context.append((cell.reference, str(cell.value)))
    values = _row_values(label, axis, rows)
    return QueryColumn(label.address.rstrip("0123456789"), str(label.value),
                       label.reference, tuple(cell.value for cell in values),
                       number_formats=tuple(dict.fromkeys(cell.number_format for cell in values)),
                       context=tuple(context))


def _row_values(label, axis, rows):
    row = next((row for row in rows if any(cell.reference == label.reference for cell in row.cells)), None)
    if row is None:
        return []
    left = _column(label)
    right = min((_column(cell) for cell in row.cells if _column(cell) > left and _human_label(cell)), default=16_385)
    periods = {_column(cell) for cell in axis.cells if source_period(cell.value)}
    return [cell for cell in row.cells if left < _column(cell) < right and _column(cell) in periods
            and (_numeric(cell.value) or cell.formula and cell.value is None)]


def row_metric_conflict(label, axis, rows, question):
    return column_metric_conflict(row_metric_column(label, axis, rows), question)
