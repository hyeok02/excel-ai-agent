"""Re-read context references from this request's authorized workbook only."""
from app.agent.query.references import _box, _contains, matching_references, normalize_reference
from app.agent.query.tabular_catalog import build_query_tables

MAX_CONTEXT_CHARACTERS = 24_000
MAX_ITEM_CELLS = 24


def source_bound_context(context, summary, index) -> list[dict]:
    if context is None:
        return []
    cells = {normalize_reference(cell.reference): cell for row in index.rows for cell in row.cells}
    available = set(cells)
    tables = build_query_tables(summary)
    entries, size = [], 0
    # Recency matters under the character budget. Original IDs survive filtering.
    items = [(f"turn:{i}", turn) for i, turn in reversed(list(enumerate(context.turns)))]
    items += [(f"insight:{i}", insight) for i, insight in enumerate(context.insights)]
    for key, item in items:
        matched = set()
        for ref in item.evidence:
            normalized = normalize_reference(ref)
            if normalized:
                matched.update(matching_references(normalized, available))
        if not matched:
            continue
        selected = [cells[ref] for ref in cells if ref in matched][:MAX_ITEM_CELLS]
        headers, neighbors = [], []
        for table in tables:
            bounds = _box(table.id)
            if bounds is None or not any(
                (cell_box := _box(ref)) and _contains(bounds, cell_box) for ref in matched
            ):
                continue
            headers.extend(cells[ref] for column in table.columns
                           if (ref := normalize_reference(column.header_reference)) in cells)
            for cell in selected:
                cell_box = _box(cell.reference)
                if cell_box and _contains(bounds, cell_box):
                    neighbors.extend(cells[ref] for column in table.columns[:12]
                                     if (ref := normalize_reference(
                                         f"{table.sheet_name}!{column.id}{cell_box.min_row}"
                                     )) in cells and ref not in matched)
        unique = {cell.reference: cell for cell in [*selected[:12], *headers[:6], *neighbors[:6]]}
        entry = {
            "id": key,
            "hint": item.model_dump(exclude={"evidence"}),
            "source_cells": [
                {"reference": cell.reference, "value": _value(cell.value)}
                for cell in list(unique.values())[:MAX_ITEM_CELLS]
            ],
        }
        length = len(str(entry))
        if size + length <= MAX_CONTEXT_CHARACTERS:
            entries.append(entry)
            size += length
    return entries


def _value(value):
    return value[:240] if isinstance(value, str) else value
