"""Recover complete original rectangles; never use a sampled table as a series."""
from openpyxl.utils import coordinate_to_tuple, get_column_letter, range_boundaries

from app.agent.query.streaming_tabular_rows import header_matches, metadata_matches, source_scope
from app.agent.query.tabular_validation import validated_table
from app.agent.query.workbook_source import source_for
from app.agent.query.workbook_source_models import SourceReadError


def table_rows(table, tables, index, question):
    """Return exact source rows, including headers, and a bounded-read error."""
    if table.complete and validated_table(table, index, set()):
        from app.agent.query.index import IndexedRow

        left, top, right, bottom = range_boundaries(table.reference)
        rows = [IndexedRow(row.sheet_name, row.row_number, tuple(
            cell for cell in row.cells if left <= coordinate_to_tuple(cell.address)[1] <= right))
                for row in index.rows if row.sheet_name == table.sheet_name
                and top <= row.row_number <= bottom and row.row_number not in table.metadata_rows]
        return rows, None
    provider = source_for(index)
    if provider is None:
        return [], "incomplete_source"
    try:
        sheet = source_scope(provider, index, table, set(), tables, question)
        if sheet is None:
            return [], "ambiguous_source_scope"
        rows = []
        _, top, _, bottom = range_boundaries(table.reference)
        scan = provider.scan_rows(table.sheet_name, table.reference)
        with scan as source:
            for row in source:
                if row.sheet_name != table.sheet_name or row.row_number != top + len(rows):
                    return [], "incomplete_source"
                if not rows and not header_matches(row, table):
                    return [], "source_mismatch"
                if row.row_number in table.metadata_rows and not metadata_matches(row, table):
                    return [], "source_mismatch"
                rows.append(row)
                if len(rows) > 20_001:
                    return [], "resource_limit"
        if not scan.complete or len(rows) != bottom - top + 1:
            return [], "incomplete_source"
        return [row for row in rows if row.row_number not in table.metadata_rows], None
    except (SourceReadError, ValueError, TypeError):
        return [], "incomplete_source"


def rectangle_rows(sheet, reference, raw, complete, index):
    """Horizontal reports require complete summaries, rechecked cell by cell."""
    if not complete or index.truncated_for({sheet}):
        return [], "incomplete_source"
    from app.agent.query.index import IndexedRow
    from app.agent.query.tabular_catalog_sources import cell_value
    from app.agent.query.tabular_filters import same_value

    left, top, right, bottom = range_boundaries(reference)
    rows = []
    found = {}
    for row in index.rows:
        if row.sheet_name != sheet or not top <= row.row_number <= bottom:
            continue
        cells = tuple(cell for cell in row.cells if left <= coordinate_to_tuple(cell.address)[1] <= right)
        rows.append(IndexedRow(sheet, row.row_number, cells))
        found.update((cell.address, cell) for cell in cells)
    for address in set(raw) | set(found):
        row, column = coordinate_to_tuple(address)
        if not (top <= row <= bottom and left <= column <= right):
            continue
        expected, actual = raw.get(address, {}), found.get(address)
        if not same_value(cell_value(expected), actual.value if actual else None):
            return [], "source_mismatch"
        if (expected.get("formula") or None) != (actual.formula if actual else None):
            return [], "source_mismatch"
        if actual and actual.value is not None and str(expected.get("number_format") or "General") != actual.number_format:
            return [], "source_mismatch"
    return rows, None


def column_cells(row):
    return {get_column_letter(coordinate_to_tuple(cell.address)[1]): cell for cell in row.cells}
