"""Bind dates before checking values, without discarding unknown-date records."""
import re
from openpyxl.utils import range_boundaries

from app.agent.query.ambiguity_labels import mentioned_sources
from app.agent.query.metric_observation_cells import MetricObservation, _human_label, _column, _sheet_rows
from app.agent.query.metric_observation_periods import source_period
from app.agent.query.metric_observations import _period_cells
from app.agent.query.trend_date_bounds import (
    _DATE_WORDS, _UNSUPPORTED_DATE, parse_trend_date_bounds, select_trend_periods,
)
from app.agent.query.trend_relative_dates import RELATIVE_CUE
from app.agent.query.trend_date_qualifiers import _MONTH, _FISCAL, _QUARTER
from app.agent.query.trend_labels import trend_metric_label_matches


def source_scope_names(index, question, tables):
    """Keep dates inside other requested source names out of calendar syntax.

    Bind actual column headers or labels below a horizontal date axis, not
    arbitrary workbook prose. Final coverage still requires valid series.
    """
    if not (re.search(r"\d{4}", question) or RELATIVE_CUE.search(question)
            or any(pattern.search(question) for pattern in (_UNSUPPORTED_DATE, _DATE_WORDS, _MONTH, _FISCAL, _QUARTER))):
        return ()
    cells = {cell.reference: cell for row in index.rows for cell in row.cells}
    names = {str(cell.value) for table in tables for column in table.columns
             if (cell := cells.get(column.header_reference)) is not None
             and _human_label(cell) and trend_metric_label_matches(column.header, question)}
    names.update(mentioned_sources({row.sheet_name for row in index.rows}, question))
    for sheet, rows in _sheet_rows(index.rows).items():
        axes = [(row.row_number, _period_cells(row)) for row in rows]
        axes = [(number, dates) for number, dates in axes if len(dates) >= 2]
        rectangles = [range_boundaries(table.reference) for table in tables if table.sheet_name == sheet]
        for row in rows:
            for cell in row.cells:
                if not _human_label(cell) or not trend_metric_label_matches(str(cell.value), question):
                    continue
                if _dated_label(cell, row, axes, rectangles):
                    names.add(str(cell.value))
    return tuple(sorted(names))


def _dated_label(cell, row, axes, rectangles):
    for left, top, right, bottom in rectangles:
        if not left <= _column(cell) <= right or not top <= row.row_number <= bottom:
            continue
        for number, dates in axes:
            if not top <= number < row.row_number or row.row_number - number > 40:
                continue
            columns = {_column(date) for date in dates if _column(cell) < _column(date) <= right}
            if len(columns) >= 2 and any(_column(value) in columns
                                         and (value.value is not None or value.formula) for value in row.cells):
                return True
    return False


def scope_dated_items(question, label, items, context=(), *, relative_error=None,
                      missing_date_error="missing_or_invalid_date", source_names=()):
    """Items carry opaque source records and original date cells, not values.

    Full rectangle/source checks happen before this step. An undated record
    cannot be proved outside the request, even if its numeric value is absent.
    Entity ambiguity may be resolved inside an absolute window, but must not
    choose a relative anchor from unrelated populations.
    """
    observations = []
    for _, cell in items:
        if cell is None:
            return (), "", missing_date_error
        period = source_period(cell.value)
        if period is None:
            return (), "", "missing_or_invalid_date"
        observations.append(MetricObservation(label, label, period, cell, None, None, (), tuple(context)))
    bounds, error = parse_trend_date_bounds(question, observations, (label.sheet_name, *source_names))
    if error:
        return (), "", f"date_scope:{error}"
    if bounds.relative and relative_error:
        return (), "", relative_error
    selected = {id(item) for item in select_trend_periods(observations, bounds)}
    if observations and not selected and (bounds.start is not None or bounds.end is not None):
        return (), bounds.note, "outside_requested_period"
    return tuple(record for (record, _), point in zip(items, observations) if id(point) in selected), bounds.note, None
