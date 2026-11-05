"""Source tables an edit rule may name, and the catalog the model reads them from.

These are the question catalog's tables plus regions it cannot type because a
title sits above the header or notes sit below the last record ("Percentage of
days …" / Year, Good, … / "Data: EPA …"). Such a region is narrowed to its header
row and record rows, and is then built and checked exactly like any other table.
A header may name periods with whole numbers (Indicator, 1997, 1998, … 2024): the
years become that table's column names, so "2019년" maps onto the 2019 column.
Each text column lists its distinct source values so a word such as "쿠키" can be
mapped onto a value that really exists.
"""
import re
from dataclasses import replace

from openpyxl.utils import coordinate_to_tuple, get_column_letter, range_boundaries

from app.agent.query.tabular_catalog import build_query_tables
from app.agent.query.tabular_catalog_builder import build_table
from app.agent.query.tabular_catalog_models import QueryRow
from app.agent.query.tabular_catalog_sources import cell_value, table_sources

MAX_TABLES = 18
MAX_COLUMNS = 60
MAX_TEXT_VALUES = 30
MAX_CHARACTERS = 30_000
TITLE_ROWS = 4
YEARS = (1800, 2200)


def writeback_tables(summary, index=None):
    """index: the edit's full index, so a sampled large table is rebuilt from every row."""
    tables = build_query_tables(summary)
    for sheet in summary.sheets:
        for reference, cells, complete, merged, hidden, _ in table_sources(sheet):
            if any(table.sheet_name == sheet.name and _overlaps(table.reference, reference) for table in tables):
                continue
            narrowed = _narrowed(reference, cells)
            table = (build_table(sheet.name, narrowed, _year_names(narrowed, cells), complete, merged, hidden)
                     if narrowed else None)
            if table is not None:
                tables.append(table)
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


def _narrowed(reference, cells):
    """Header = first row (among the top few) with two text labels; records end before trailing notes."""
    left, top, right, bottom = range_boundaries(reference)
    filled = {}
    for address, raw in sorted(cells.items(), key=lambda item: coordinate_to_tuple(item[0])):
        row, column = coordinate_to_tuple(address)
        if top <= row <= bottom and left <= column <= right and cell_value(raw) not in (None, ""):
            filled.setdefault(row, []).append(cell_value(raw))
    header = next((row for row in range(top, min(bottom, top + TITLE_ROWS) + 1)
                   if sum(isinstance(value, str) for value in filled.get(row, [])) >= 2
                   or _labels_and_years(filled.get(row, []))), None)
    last = max((row for row, values in filled.items() if len(values) >= 2), default=None)
    if header is None or last is None or last <= header or (header, last) == (top, bottom):
        return None
    return f"{get_column_letter(left)}{header}:{get_column_letter(right)}{last}"


def _labels_and_years(values):
    """A row label followed by increasing whole-number years: Indicator, 1997, 1998, …"""
    numbers = [value for value in values if not isinstance(value, str)]
    return (any(isinstance(value, str) for value in values) and len(numbers) >= 2
            and all(_year(value) for value in numbers) and all(a < b for a, b in zip(numbers, numbers[1:])))


def _year(value):
    return (isinstance(value, (int, float)) and not isinstance(value, bool)
            and float(value).is_integer() and YEARS[0] <= value <= YEARS[1])


def _year_names(reference, cells):
    """Whole-number year headers read as the column names "1997", "1998", …"""
    left, top, right, _ = range_boundaries(reference)
    named = dict(cells)
    for column in range(left, right + 1):
        address = f"{get_column_letter(column)}{top}"
        raw = cells.get(address, {})
        if not raw.get("formula") and _year(raw.get("value")):
            named[address] = {**raw, "value": str(int(raw["value"]))}
    return named


def _overlaps(first, second):
    a, b, c, d = range_boundaries(first)
    e, f, g, h = range_boundaries(second)
    return a <= g and e <= c and b <= h and f <= d
