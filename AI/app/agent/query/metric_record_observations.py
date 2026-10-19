"""Pair record metrics with their own as-of dates and source identities."""
from app.agent.query.index import IndexedRow
from app.agent.query.metric_observation_periods import source_period, source_period_grain
from app.agent.query.metric_observation_cells import (
    MetricObservation, _DATE_HEADER, _METRIC_MODIFIERS, _human_label, _column,
    _numeric, _sheet_rows, _text_in_question, _normal, metric_label_matches,
)

def dated_record_observations(rows: list[IndexedRow], question: str) -> list[MetricObservation]:
    """Pair a numeric column with its own As Of column and a matched row ID.

    A nearby transaction date cannot supply a headcount date: date-header words
    must share the metric's name, or be the table's sole unqualified Date.
    """
    observations = []
    for sheet_rows in _sheet_rows(rows).values():
        for header in sheet_rows:
            labels = [cell for cell in header.cells if _human_label(cell)]
            metrics = [cell for cell in labels if metric_label_matches(str(cell.value), question)
                       and not _DATE_HEADER.search(str(cell.value))]
            dates = [cell for cell in labels if _DATE_HEADER.search(str(cell.value))]
            for metric in metrics:
                compatible = [cell for cell in dates if _shared_metric_date(metric, cell)]
                if not compatible and len(dates) == 1 and _generic_date(dates[0]):
                    compatible = dates
                if len(compatible) != 1:
                    continue
                date_header = compatible[0]
                for row in sheet_rows:
                    if not header.row_number < row.row_number <= header.row_number + 3000:
                        continue
                    cells = {_column(cell): cell for cell in row.cells}
                    value = cells.get(_column(metric))
                    date_cell = cells.get(_column(date_header))
                    if value is None or date_cell is None or not _numeric(value.value):
                        continue
                    period = source_period(date_cell.value)
                    if period is None:
                        continue
                    identifiers = [cell for cell in row.cells if _human_label(cell)
                                   and _text_in_question(str(cell.value), question)]
                    if not identifiers:
                        continue
                    # Do not let the header drift into a separate table later
                    # on the sheet with unrelated columns.
                    if _record_header_changed(sheet_rows, header, row, metric, date_header):
                        continue
                    observations.append(MetricObservation(
                        metric, value, period, date_cell, source_period_grain(date_cell.value), None,
                        (date_header,), tuple(identifiers),
                    ))
    return observations

def _record_header_changed(rows, header, data, metric, date_header):
    for row in rows:
        if not header.row_number < row.row_number < data.row_number:
            continue
        cells = {_column(cell): cell for cell in row.cells}
        candidate = cells.get(_column(date_header))
        value = cells.get(_column(metric))
        if candidate and value and _human_label(candidate) and _human_label(value):
            if _DATE_HEADER.search(str(candidate.value)) and candidate.value != date_header.value:
                return True
    return False

def _shared_metric_date(metric, date):
    metric_words = set(_normal(_METRIC_MODIFIERS.sub(" ", str(metric.value))).split())
    date_words = set(_normal(_DATE_HEADER.sub(" ", str(date.value))).split())
    return bool(metric_words & date_words)

def _generic_date(cell):
    return _normal(str(cell.value)) in {"date", "period", "as of", "날짜", "기준일", "일자"}
