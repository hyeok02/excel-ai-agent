"""Bind parent captions to a column by coordinates, including merged headers."""
from openpyxl.utils import coordinate_to_tuple, range_boundaries, get_column_letter

from app.agent.query.tabular_catalog_sources import cell_value


def column_context(sheet, column, cells, merged, reference):
    row, number = coordinate_to_tuple(column.header_reference.rsplit("!", 1)[1])
    result = []
    table_left = range_boundaries(reference)[0]
    for previous in range(max(1, row - 3), row):
        anchor = f"{column.id}{previous}"
        for span in merged:
            left, top, right, bottom = range_boundaries(span)
            if left <= number <= right and top <= previous <= bottom and bottom < row:
                anchor = span.split(":", 1)[0]
                break
        raw = cells.get(anchor, {})
        # Center-across-selection captions are not merged in OOXML. A bold
        # parent caption continues until the next caption on the same row.
        if cell_value(raw) in (None, ""):
            for preceding in range(number - 1, table_left - 1, -1):
                address = f"{get_column_letter(preceding)}{previous}"
                candidate = cells.get(address, {})
                if cell_value(candidate) not in (None, ""):
                    if candidate.get("bold") and isinstance(cell_value(candidate), str):
                        anchor, raw = address, candidate
                    break
        text = cell_value(raw)
        if isinstance(text, str) and text.strip():
            result.append((f"{sheet}!{anchor}", text.strip()))
    return tuple(dict.fromkeys(result))
