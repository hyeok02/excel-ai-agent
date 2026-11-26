"""Tables too large for the workbook summary's sample, read whole from the source for the GPT-chosen calculation.

A 1,450-row list of 43 columns is summarized from its first rows only (complete=False); "TV Show 비중" needs
every row, so the table's own range is read again from the original file, row by row, under its columns.
"""
from dataclasses import replace

from openpyxl.utils import column_index_from_string, range_boundaries

MAX_ROWS = 200_000


def completed_tables(tables, index):
    found = []
    for table in tables:
        if not table.complete and table.columns:
            table = _read(table, index) or table
        if table.complete and table.rows:
            found.append(table)
    return found


def _read(table, index):
    from app.agent.query.streaming_tabular_rows import source_row
    from app.agent.query.workbook_source import source_for
    from app.agent.query.workbook_source_models import SourceReadError
    provider = source_for(index)
    if provider is None:
        return None
    provider = replace(provider)  # its own read budget: the questions after this one keep theirs
    _, top, _, bottom = range_boundaries(table.reference)
    if bottom - top > MAX_ROWS:
        return None
    skipped = set(table.excluded_rows) | set(table.metadata_rows)
    rows = []
    try:
        with provider.scan_rows(table.sheet_name, table.reference) as scanned:
            for indexed in scanned:
                if indexed.sheet_name != table.sheet_name or indexed.row_number <= top or indexed.row_number in skipped:
                    continue
                row = source_row(indexed, table)
                if row.formulas or any(value not in (None, "") for value in row.values.values()):
                    rows.append(row)
    except (SourceReadError, OSError, ValueError):
        return None
    return replace(table, rows=tuple(rows), complete=True) if rows else None


def scoped_tables(tables, scopes):
    """The tables a question's range overlaps, cut to its rows and columns: 'Sales!A1:D3' is rows 2-3, not the table."""
    found = []
    for table in tables:
        for sheet, cells in scopes:
            if sheet == table.sheet_name and _overlaps(table.reference, cells):
                found.append(_cut(table, cells))
                break
    return [table for table in found if table.rows]


def _cut(table, cells):
    left, top, right, bottom = range_boundaries(cells.replace("$", ""))
    rows = tuple(row for row in table.rows if top <= row.row_number <= bottom)
    columns = tuple(column for column in table.columns if left <= column_index_from_string(
        "".join(ch for ch in column.header_reference.rpartition("!")[2] if ch.isalpha()).upper()) <= right)
    if len(rows) == len(table.rows) and len(columns) == len(table.columns):
        return table
    return replace(table, rows=rows, columns=columns or table.columns)


def _overlaps(first, second):
    (a, b, c, d), (e, f, g, h) = (range_boundaries(item.replace("$", "")) for item in (first, second))
    return a <= g and e <= c and b <= h and f <= d
