"""Source tables an edit rule may name, and the catalog the model reads them from.

These are the question catalog's tables plus regions it cannot type because a
title sits above the header or notes sit below the last record ("Percentage of
days …" / Year, Good, … / "Data: EPA …"). Such a region is narrowed to its header
row and record rows, and is then built and checked exactly like any other table.
Each text column lists its distinct source values so a word such as "쿠키" can be
mapped onto a value that really exists.
"""
from openpyxl.utils import coordinate_to_tuple, get_column_letter, range_boundaries

from app.agent.query.tabular_catalog import build_query_tables
from app.agent.query.tabular_catalog_builder import build_table
from app.agent.query.tabular_catalog_sources import cell_value, table_sources

MAX_TABLES = 18
MAX_COLUMNS = 60
MAX_TEXT_VALUES = 30
MAX_CHARACTERS = 30_000
TITLE_ROWS = 4


def writeback_tables(summary):
    tables = build_query_tables(summary)
    for sheet in summary.sheets:
        for reference, cells, complete, merged, hidden, _ in table_sources(sheet):
            if any(table.sheet_name == sheet.name and _overlaps(table.reference, reference) for table in tables):
                continue
            narrowed = _narrowed(reference, cells)
            table = build_table(sheet.name, narrowed, cells, complete, merged, hidden) if narrowed else None
            if table is not None:
                tables.append(table)
    return tables


def writeback_catalog(summary):
    catalog, size = [], 0
    for table in writeback_tables(summary)[:MAX_TABLES]:
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


def _narrowed(reference, cells):
    """Header = first row (among the top few) with two text labels; records end before trailing notes."""
    left, top, right, bottom = range_boundaries(reference)
    filled = {}
    for address, raw in cells.items():
        row, column = coordinate_to_tuple(address)
        if top <= row <= bottom and left <= column <= right and cell_value(raw) not in (None, ""):
            filled.setdefault(row, []).append(cell_value(raw))
    header = next((row for row in range(top, min(bottom, top + TITLE_ROWS) + 1)
                   if sum(isinstance(value, str) for value in filled.get(row, [])) >= 2), None)
    last = max((row for row, values in filled.items() if len(values) >= 2), default=None)
    if header is None or last is None or last <= header or (header, last) == (top, bottom):
        return None
    return f"{get_column_letter(left)}{header}:{get_column_letter(right)}{last}"


def _overlaps(first, second):
    a, b, c, d = range_boundaries(first)
    e, f, g, h = range_boundaries(second)
    return a <= g and e <= c and b <= h and f <= d
