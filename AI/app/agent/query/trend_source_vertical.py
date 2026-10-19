"""Extract one date-aligned metric without merging record identities."""
import re
from dataclasses import replace

from app.agent.query.metric_observation_cells import (
    MetricObservation, _DATE_HEADER, _numeric, _text_in_question,
)
from app.agent.query.metric_observation_periods import source_period, source_period_grain
from app.agent.query.trend_source_models import MAX_TREND_OBSERVATIONS, TrendCandidate
from app.agent.query.trend_source_readback import column_cells, table_rows
from app.agent.query.trend_source_context import verified_context

_IDENTITY = re.compile(r"\b(?:id|code|identifier|key)\b|코드|식별자|식별번호", re.I)


def vertical_candidate(table, metric, tables, index, question):
    rows, error = table_rows(table, tables, index, question)
    from app.agent.query.workbook_source import source_for
    provider = source_for(index)
    hidden = set(table.excluded_rows)
    if provider:
        if table.sheet_name not in provider.authorized_sheets:
            return TrendCandidate(table.id, (), error="ambiguous_source_scope")
        row_numbers = {row.row_number for row in rows}
        hidden.update(number for number in provider.sheet(table.sheet_name).hidden_rows
                      if number in row_numbers)
    base = TrendCandidate(table.id, (), error=error, hidden_rows=len(hidden))
    if error:
        return base
    captions = verified_context(table.context, index)
    if captions is None:
        return replace(base, error="source_mismatch")
    cells = {cell.reference: cell for row in rows for cell in row.cells}
    label = cells.get(metric.header_reference)
    if label is None:
        return replace(base, error="source_mismatch")
    header_row = int(re.search(r"\d+$", label.address)[0])
    records = [column_cells(row) for row in rows if row.row_number > header_row
               and row.row_number not in hidden and row.cells]
    dates = [column for column in table.columns if column.id != metric.id
             and _DATE_HEADER.search(column.header)]
    if not dates:
        dates = [column for column in table.columns if column.id != metric.id
                 and sum(bool(source_period(row[column.id].value)) for row in records
                         if column.id in row and isinstance(row[column.id].value, str)) >= 2]
    if len(dates) != 1:
        return replace(base, context=(label,), error="ambiguous_date_axis")
    date = dates[0]
    date_header = cells.get(date.header_reference)
    if date_header is None:
        return replace(base, context=(label,), error="source_mismatch")
    records, identities, error = _identity_records(table, records, metric.id, date.id, question)
    context = (label, date_header, *identities, *captions)
    if error:
        return replace(base, context=context, error=error)
    observations = []
    for row in records:
        value, period_cell = row.get(metric.id), row.get(date.id)
        # Rows occupied in a rectangle cannot disappear because one axis is blank.
        if value is None or period_cell is None or not _numeric(value.value):
            return replace(base, context=context, error="missing_or_invalid_value")
        period = source_period(period_cell.value)
        if period is None:
            return replace(base, context=context, error="missing_or_invalid_date")
        observations.append(MetricObservation(label, value, period, period_cell, source_period_grain(period_cell.value), None,
                                              (date_header,), tuple([*identities, *captions])))
        if len(observations) > MAX_TREND_OBSERVATIONS:
            return replace(base, context=context, error="resource_limit")
    return replace(base, observations=tuple(observations), context=context,
                   error=None if len(observations) >= 2 else "insufficient_periods")


def _identity_records(table, records, metric, date, question):
    identities = []
    for column in table.columns:
        if column.id in {metric, date}:
            continue
        values = [row.get(column.id) for row in records]
        texts = [cell for cell in values if cell and isinstance(cell.value, str)
                 and cell.value.strip() and source_period(cell.value) is None]
        if not texts and not _IDENTITY.search(column.header):
            continue
        distinct = {(type(cell.value).__name__, cell.value) for cell in values if cell and cell.value is not None}
        if len(distinct) <= 1 and all(cell and cell.value is not None for cell in values):
            identities.extend(values[:1])
            continue
        selected = [cell for cell in texts if _text_in_question(str(cell.value), question)]
        choices = {cell.value for cell in selected}
        if len(choices) != 1:
            return records, identities, "ambiguous_entity_scope"
        wanted = next(iter(choices))
        if any(cell is None or cell.value is None for cell in values):
            return records, identities, "missing_entity"
        records = [row for row in records if row[column.id].value == wanted]
        identities.append(selected[0])
    return records, identities, None
