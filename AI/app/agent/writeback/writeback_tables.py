"""Source tables an edit rule may name, and the catalog the model reads them from.

These are the question catalog's tables, including regions read without a title
above or notes below and tables whose headers are years (tabular_narrowed_tables).
Each text column lists its distinct source values so a word such as "쿠키" can be
mapped onto a value that really exists.
"""
import re
from dataclasses import replace

from openpyxl.utils import range_boundaries

from app.agent.query.tabular_catalog import build_query_tables
from app.agent.query.tabular_catalog_models import QueryRow

MAX_TABLES = 18
MAX_COLUMNS = 60
MAX_TEXT_VALUES = 30
MAX_CHARACTERS = 30_000


def writeback_tables(summary, index=None):
    """index: the edit's full index, so a sampled large table is rebuilt from every row."""
    tables = build_query_tables(summary, text_regions=True)
    return [_completed(table, index) for table in tables] if index is not None else tables


def _completed(table, index):
    """The summary keeps a sample of a large sheet; the edit index holds every row of it."""
    if table.complete or index.truncated_for({table.sheet_name}):
        return table
    left, top, right, bottom = range_boundaries(table.reference)
    letters = {column.id: re.search(r"([A-Z]+)\d+$", column.header_reference.upper()).group(1)
               for column in table.columns}
    skipped = table.excluded_rows | table.metadata_rows
    rows = []
    for row in index.rows:
        if row.sheet_name != table.sheet_name or not top < row.row_number <= bottom or row.row_number in skipped:
            continue
        cells = {cell.address: cell for cell in row.cells}
        found = {column: cells.get(f"{letter}{row.row_number}") for column, letter in letters.items()}
        values = {column: cell.value if cell else None for column, cell in found.items()}
        formulas = {column: cell.formula for column, cell in found.items() if cell and cell.formula}
        formats = {column: cell.number_format for column, cell in found.items() if cell and cell.value not in (None, "")}
        if formulas or any(value not in (None, "") for value in values.values()):
            rows.append(QueryRow(row.row_number, values, formulas, formats))
    return replace(table, rows=tuple(rows), complete=True)


def writeback_catalog(summary, index=None):
    catalog, size = [], 0
    for table in writeback_tables(summary, index)[:MAX_TABLES]:
        entry = {"table_id": table.id, "sheet_name": table.sheet_name, "range": table.reference,
                 "row_count": len(table.rows), "columns": [
                     {"column_id": column.id, "header": column.display_header, "values": _values(table, column.id)}
                     for column in table.columns[:MAX_COLUMNS]]}
        if size + len(str(entry)) > MAX_CHARACTERS:
            continue
        catalog.append(entry)
        size += len(str(entry))
    return catalog


def _values(table, column):
    seen = list(dict.fromkeys(row.values.get(column) for row in table.rows
                              if row.values.get(column) not in (None, "")))
    texts = [value for value in seen if isinstance(value, str)]
    return texts[:MAX_TEXT_VALUES] if len(texts) == len(seen) else seen[:3]


