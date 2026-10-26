"""Small readable previews retain the exact source cells behind every value."""
from datetime import datetime
import re

from app.agent.query.clarification_preview_scope import absent_source_value
from app.agent.query.metric_observation_cells import MetricObservation, _DATE_HEADER
from app.agent.query.metric_observation_periods import source_period
from app.agent.query.metric_observation_render import _value
from app.agent.query.metric_observation_units import observation_unit

_IDENTITY_HEADER = re.compile(r"\b(?:company|entity|issuer|organization|name|identifier|id)\b|회사|기업|이름|명칭|대상", re.I)


def preview_row(table, column, row, cells, index_rows):
    label = cells.get(column.header_reference)
    value = cells.get(f"{table.sheet_name}!{column.id}{row.row_number}")
    if label is None or value is None or value.value != row.values.get(column.id):
        return None
    references = [label, value]
    dates, identities = [], []
    for other in table.columns:
        if other.id == column.id or other.id in table.hidden_columns:
            continue
        cell = cells.get(f"{table.sheet_name}!{other.id}{row.row_number}")
        header = cells.get(other.header_reference)
        if header is not None and (cell is None or absent_source_value(cell.value)):
            if _IDENTITY_HEADER.search(other.header):
                identities.append(f"대상 미확인 ({other.header})")
                references.extend((header, cell) if cell is not None else (header,))
            continue
        if cell is None or header is None or cell.value != row.values.get(other.id):
            continue
        if _DATE_HEADER.search(other.header) and source_period(cell.value):
            dates.append(f"{other.header}: {cell.value}")
            references.extend((header, cell))
        elif isinstance(cell.value, str) and cell.value.strip() and not source_period(cell.value):
            identities.append(f"{other.header}: {str(cell.value)[:100]}")
            references.extend((header, cell))
    item = MetricObservation(label, value, datetime.min, label, None, None, ())
    unit = observation_unit(item, index_rows)
    references.extend(unit.references)
    displayed = _value(item, unit) if isinstance(value.value, (int, float)) and not isinstance(value.value, bool) \
        else str(value.value)[:160]
    text = " · ".join([*identities[:2], *dates[:2], f"값: {displayed} ({value.address})"])
    return text, tuple(dict.fromkeys(references)), bool(dates), unit.known


def latest_preview_rows(question, table, metric, rows, complete):
    from app.agent.query.metric_observation_periods import LATEST
    if not LATEST.search(question):
        return rows, ""
    uncertain = "최신 값 미확인: 아래 값은 원본 예시이며 현재 값으로 확정하지 않았습니다."
    if not complete:
        return rows, uncertain
    date_columns = [column for column in table.columns if _DATE_HEADER.search(column.header)
                    and column.id not in table.hidden_columns]
    if len(date_columns) != 1:
        return rows, uncertain
    dated = [(row, source_period(row.values.get(date_columns[0].id))) for row in rows]
    if not dated or any(date is None for _, date in dated):
        return rows, uncertain
    identities = [column.id for column in table.columns
                  if column.id not in {date_columns[0].id, metric.id} and column.id not in table.hidden_columns
                  and any(isinstance(row.values.get(column.id), str) for row in rows)
                  and all(row.values.get(column.id) is None or isinstance(row.values.get(column.id), str)
                          for row in rows)]
    def scope(row):
        return tuple((key, row.values.get(key)) for key in identities)
    newest = {}
    for row, date in dated:
        newest[scope(row)] = max(newest.get(scope(row), date), date)
    return [row for row, date in dated if date == newest[scope(row)]], ""
