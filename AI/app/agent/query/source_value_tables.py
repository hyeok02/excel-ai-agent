"""Record-table cells whose header and row labels explain every question term."""
import re
from dataclasses import dataclass
from datetime import datetime

from app.agent.query.metric_observation_cells import metric_label_matches
from app.agent.query.source_value_terms import FIELD_ONLY, FIELD_TERMS, MEASURES, RATIO_TERMS, covers, tokens
from app.agent.query.source_value_cells import (
    as_date as _as_date, is_number as _is_number, matches as _matches, usable as _usable,
)
from app.agent.query.tabular_catalog import build_query_tables

_LEGAL = {"inc", "corp", "corporation", "co", "ltd", "llc", "plc", "lp", "sa", "ag", "ab", "publ", "the"}
_CODE = re.compile(r"[A-Z0-9]+(?:_[A-Z0-9]+)+|SPGTable")
_DATE_HEADER = re.compile(r"^(?:dates?|period(?: ended)?|as of|날짜|일자|기준일)$", re.I)
_RATIO = re.compile(r"\(\s*x\s*\)|\bmultiple|/\s*(?:ebitda|ebit|revenue|sales|eps|book|equity|earnings)", re.I)


@dataclass(frozen=True)
class SourceValue:
    rank: tuple
    sheet: str
    address: str
    value: object
    header: str
    header_address: str
    label: str = ""
    label_address: str = ""
    period: datetime | None = None
    latest: bool = False  # chosen as the newest row of a single time series


VETO = "unresolved"  # a matching field whose row the question cannot select


def table_values(question_terms, summary):
    period, fields, words = question_terms
    found = []
    for table in build_query_tables(summary):
        columns = [column for column in table.columns if column.id not in table.hidden_columns
                   and not _CODE.fullmatch(column.header.strip())]
        dates = _date_column(table, columns)
        for column in columns:
            found += _column_values(table, columns, column, dates, period, fields, words)
    return found


def _column_values(table, columns, column, dates, period, fields, words):
    header = column.display_header
    if _RATIO.search(header) and not RATIO_TERMS & set(fields):
        return []
    units = (*fields, *words)
    in_header = {unit for unit in units if _covers(unit, header)}
    # "Engineering 인원": a named breakdown of the table's Total Employees.
    if in_header & set(words) and any(unit in MEASURES and unit not in in_header
                                      and _total_covers(unit, columns) for unit in fields):
        in_header |= {unit for unit in fields if unit in MEASURES}
    if not in_header or FIELD_ONLY & set(fields) - in_header:
        return []
    numeric = _numeric_share(table, column) >= 0.5
    exact = int(all(token in _LEGAL or token.isdigit() or any(_covers(unit, token) for unit in in_header)
                    for token in tokens(re.sub(r"\([^)]*\)", " ", header))))
    found, plain = [], []
    for row in table.rows:
        value = row.values.get(column.id)
        if not _usable(value) or numeric and not _is_number(value):
            continue
        labels = [(other, row.values.get(other.id)) for other in columns
                  if other.id != column.id and isinstance(row.values.get(other.id), str)]
        rest = [unit for unit in units if unit not in in_header]
        day = _as_date(row.values.get(dates.id)) if dates else None
        if period and not (day and _matches(day, period)):
            continue
        label, ratio = _label(labels, rest)
        if rest and label is None:
            continue
        item = SourceValue((exact, ratio), table.sheet_name, f"{column.id}{row.row_number}", value,
                           column.header, column.header_reference,
                           str(label[1]) if label else "", f"{label[0].id}{row.row_number}" if label else "", day)
        (found if rest or period else plain).append(item)
    if found or not plain:
        return found
    if len(table.rows) == 1 and table.complete:
        return plain
    if (table.complete and dates and all(item.period for item in plain)
            and len({item.period for item in plain}) == len(plain)):
        newest = max(plain, key=lambda item: item.period)
        return [SourceValue(**{**newest.__dict__, "latest": True})]
    return [VETO]


def _label(labels, rest):
    """The row label that names every remaining term, preferring a full name."""
    if not rest:
        return None, 1.0
    best, score = None, 0.0
    for column, text in labels:
        if not all(_covers(unit, text) for unit in rest):
            continue
        words = [token for token in tokens(text) if token not in _LEGAL]
        ratio = sum(any(_covers(unit, word) for unit in rest) for word in words) / max(len(words), 1)
        if ratio > score:
            best, score = (column, text), ratio
    return best, score


def _covers(unit, text):
    return covers(unit, text) or (unit not in FIELD_TERMS and re.fullmatch(r"[가-힣]+", unit) is not None
                                  and metric_label_matches(str(text), unit))


def _total_covers(unit, columns):
    return any(column.header.casefold().startswith(("total", "전체", "총")) and covers(unit, column.header)
               for column in columns)


def _date_column(table, columns):
    """The record date: a date-named header first, else the most date-filled column."""
    scored = []
    for column in columns:
        values = [row.values.get(column.id) for row in table.rows]
        share = sum(_as_date(value) is not None for value in values) / max(len(values), 1)
        if share >= 0.8 and len(values) >= 2:
            scored.append((bool(_DATE_HEADER.match(column.header.strip())), share, -columns.index(column), column))
    return max(scored, key=lambda item: item[:3])[-1] if scored else None


def _numeric_share(table, column):
    values = [row.values.get(column.id) for row in table.rows if _usable(row.values.get(column.id))]
    return sum(_is_number(value) for value in values) / len(values) if values else 0
