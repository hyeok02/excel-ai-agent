"""Expose unambiguous source-table header bindings, not guessed descriptions."""
from app.agent.query.references import _box, _contains, normalize_reference
from app.agent.query.tabular_catalog import build_query_tables


def source_header_bindings(summary, index, evidence):
    original = {normalize_reference(cell.reference): cell for row in index.rows for cell in row.cells}
    candidates = {}
    for item in evidence[:120]:
        reference = normalize_reference(f"{item.sheet_name}!{item.reference}")
        cell = original.get(reference)
        if cell and type(cell.value) is type(item.value) and cell.value == item.value:
            candidates[reference] = cell
    bindings = {}
    for table in build_query_tables(summary):
        bounds = _box(table.id)
        rows = {row.row_number for row in table.rows}
        for reference, cell in candidates.items():
            position = _box(reference)
            if not bounds or not position or not _contains(bounds, position) or position.min_row not in rows:
                continue
            for column in table.columns:
                header_ref = normalize_reference(column.header_reference)
                header = original.get(header_ref)
                column_box = _box(column.header_reference)
                if (column_box and column_box.min_column == position.min_column
                        and header and header.formula is None and header.value == column.header):
                    bindings.setdefault(reference, set()).add(header_ref)
    return {reference: next(iter(headers)) for reference, headers in bindings.items() if len(headers) == 1}
