"""Expose source headers and bounded samples for schema-grounded query planning."""
import re

from openpyxl.utils import get_column_letter, range_boundaries

from app.agent.query.tabular_catalog_models import QueryColumn, QueryRow, QueryTable
from app.agent.query.tabular_catalog_sources import cell_value, table_sources

MAX_CATALOG_TABLES = 18
MAX_CATALOG_COLUMNS = 80
MAX_CATALOG_CHARACTERS = 30_000


def build_query_tables(summary) -> list[QueryTable]:
    tables = []
    for sheet in summary.sheets:
        for reference, cells, complete, merged, hidden in table_sources(sheet):
            table = _build_table(sheet.name, reference, cells, complete, merged, hidden)
            if table is not None:
                tables.append(table)
    return tables


def query_catalog(summary, question: str) -> list[dict]:
    tables = build_query_tables(summary)
    tokens = set(re.findall(r"[\w]+", question.casefold()))
    tables.sort(key=lambda table: -_relevance(table, tokens))
    catalog, size = [], 0
    for table in tables[:MAX_CATALOG_TABLES]:
        entry = {
            "table_id": table.id, "sheet_name": table.sheet_name,
            "range": table.reference, "complete": table.complete,
            "row_count": len(table.rows),
            "excluded_row_count": len(table.excluded_rows),
            "columns": [{
                "column_id": column.id, "header": column.header,
                "header_reference": column.header_reference,
                "samples": list(column.sample_values),
            } for column in table.columns[:MAX_CATALOG_COLUMNS]],
        }
        entry_size = len(str(entry))
        if size + entry_size > MAX_CATALOG_CHARACTERS:
            continue
        catalog.append(entry)
        size += entry_size
    return catalog


def _build_table(sheet, reference, cells, complete, merged, hidden):
    left, top, right, bottom = range_boundaries(reference)
    if bottom <= top or right <= left:
        return None
    headers = []
    for number in range(left, right + 1):
        column = get_column_letter(number)
        raw = cells.get(f"{column}{top}", {})
        value = cell_value(raw)
        if value is None:
            continue
        if raw.get("formula") or not isinstance(value, str) or not value.strip():
            return None
        headers.append((column, value.strip()))
    if len(headers) < 2 or len({header for _, header in headers}) != len(headers):
        return None
    if any(_data_merge(span, top, bottom, left, right) for span in merged):
        return None
    rows = []
    for number in range(top + 1, bottom + 1):
        values = {column: cell_value(cells.get(f"{column}{number}", {}))
                  for column, _ in headers}
        formulas = {column: raw["formula"] for column, _ in headers
                    if (raw := cells.get(f"{column}{number}", {})).get("formula")}
        formats = {column: str(cells.get(f"{column}{number}", {}).get("number_format") or "General")
                   for column, value in values.items() if value not in (None, "")}
        if not formulas and not any(value not in (None, "") for value in values.values()):
            continue
        rows.append(QueryRow(number, values, formulas, formats))
    if not rows:
        return None
    columns = tuple(QueryColumn(
        column, header, f"{sheet}!{column}{top}", _samples(rows, column),
        tuple(dict.fromkeys(row.number_formats[column] for row in rows if column in row.number_formats))
    ) for column, header in headers)
    return QueryTable(f"{sheet}!{reference}", sheet, reference, columns, tuple(rows), complete, hidden)


def _data_merge(span, top, bottom, left, right):
    a, b, c, d = range_boundaries(span)
    return a <= right and c >= left and b <= bottom and d >= top


def _samples(rows, column):
    values, seen = [], set()
    for row in rows:
        value = row.values[column]
        key = (type(value), str(value))
        if key not in seen:
            seen.add(key)
            values.append(value[:160] if isinstance(value, str) else value)
        if len(values) == 6:
            break
    return tuple(values)


def _relevance(table, tokens):
    source = " ".join([table.sheet_name] + [column.header for column in table.columns])
    source += " " + " ".join(str(value) for column in table.columns
                             for value in column.sample_values if value is not None)
    return sum(len(token) for token in tokens if len(token) > 1 and token in source.casefold())
