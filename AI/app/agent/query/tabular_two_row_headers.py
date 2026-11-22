"""A header written on two rows: a merged parent over its children ("2024" over 상반기 | 하반기).

    제품 |    2023     |    2024
         | 상반기 하반기 | 상반기 하반기

Each column is named by its parent and child ("2024 상반기"); a column merged down both rows
("제품") keeps its one name. Data starts on the third row. Recognised by the merges themselves:
a parent spanning several columns on the first row, and text in every child cell under it.
"""
from openpyxl.utils import coordinate_to_tuple, get_column_letter, range_boundaries

from app.agent.query.tabular_catalog_sources import cell_value


def two_row_header(cells, merged, left, top, right, bottom):
    """(headers, header references, data rows) of a two-row header, or None."""
    spans = [range_boundaries(span) for span in merged]
    parents = [span for span in spans if span[1] == span[3] == top and span[2] > span[0]]
    if not parents or bottom < top + 2:
        return None
    headers, references = [], {}
    for number in range(left, right + 1):
        column = get_column_letter(number)
        down = any(a == c == number and b == top and d >= top + 1 for a, b, c, d in spans)
        parent = next((f"{get_column_letter(a)}{top}" for a, b, c, d in parents if a <= number <= c), f"{column}{top}")
        child = f"{column}{top + 1}"
        upper, lower = cell_value(cells.get(parent, {})), cell_value(cells.get(child, {}))
        if down:
            lower = None
        elif not isinstance(lower, str) or not lower.strip():
            if any(a <= number <= c for a, b, c, d in parents):
                return None  # a child cell under a merged parent is empty: not this shape
            if upper is None:
                continue
        if upper is None and lower is None:
            continue
        names = [str(part).strip() for part in (upper, lower) if part not in (None, "") and str(part).strip()]
        if not names:
            continue
        headers.append((column, " ".join(names)))
        references[column] = f"{child if lower else parent}"
    if len(headers) < 2:
        return None
    rows = sorted({coordinate_to_tuple(address)[0] for address in cells if top + 1 < coordinate_to_tuple(address)[0] <= bottom})
    return headers, references, rows
