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
        headers, captions, neighbors = [], [], []
        for table in tables:
            bounds = _box(table.id)
            if bounds is None or not any(
                (cell_box := _box(ref)) and _contains(bounds, cell_box) for ref in matched
            ):
                continue
            cited_columns = {box.min_column for cell in selected
                             if (box := _box(cell.reference)) and _contains(bounds, box)}
            # A value in a far-right column needs its own label, not the first
            # six headers of a wide table. All candidates remain source cells.
            ordered_columns = sorted(table.columns, key=lambda column: not (
                (box := _box(column.header_reference)) and box.min_column in cited_columns
            ))
            headers.extend(cells[ref] for column in ordered_columns
                           if (ref := normalize_reference(column.header_reference)) in cells)
            captions.extend(cells[ref] for reference, _ in table.context
                            if (ref := normalize_reference(reference)) in cells)
            for cell in selected:
                cell_box = _box(cell.reference)
                if cell_box and _contains(bounds, cell_box):
                    neighbors.extend(cells[ref] for column in table.columns[:12]
                                     if (ref := normalize_reference(
                                         f"{table.sheet_name}!{column.id}{cell_box.min_row}"
                                     )) in cells and ref not in matched)
        captions = list({cell.reference: cell for cell in captions}.values())[:2]
        unique = {cell.reference: cell for cell in [
            *selected[:12], *headers[:6], *captions, *neighbors[:6 - len(captions)],
        ]}
        entry = {
            "id": key,
            "hint": item.model_dump(exclude={"evidence"}),
            "source_cells": [
                {"reference": cell.reference, "value": _value(cell.value),
                 "number_format": cell.number_format}
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
