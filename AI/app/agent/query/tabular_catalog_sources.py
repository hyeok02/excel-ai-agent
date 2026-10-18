"""Recover rectangular sources without relying on semantic role classifications."""
from collections import defaultdict
from dataclasses import asdict, is_dataclass

from openpyxl.utils import coordinate_to_tuple, get_column_letter, range_boundaries
from app.agent.query.tabular_report_sources import leaf_header_row, report_ranges


def source_cells(region) -> dict[str, dict]:
    if getattr(region, "query_complete", None) is not None:
        rows = region.query_rows
    elif region.analysis_complete or region.analysis_rows:
        rows = region.analysis_rows
    else:
        rows = region.preview_rows
    return {
        str(cell["address"]): cell
        for row in rows
        for item in row
        if (cell := asdict(item) if is_dataclass(item) else item).get("address")
    }


def cell_value(cell: dict):
    return cell.get("cached_value") if cell.get("formula") else cell.get("value")


def table_sources(sheet):
    regions = [(region, source_cells(region)) for region in sheet.regions]
    emitted = []
    for native in sheet.tables:
        left, top, right, bottom = range_boundaries(native.reference)
        bottom -= max(0, native.totals_row_count)
        reference = f"{get_column_letter(left)}{top}:{get_column_letter(right)}{bottom}"
        cells, complete, merged, hidden = _source_range(reference, regions)
        if cells:
            emitted.append(native.reference)
            yield reference, cells, complete, merged, hidden, "native"
    grouped = defaultdict(list)
    for schema in sheet.column_schemas:
        grouped[schema.source_range].append(schema)
    for reference in grouped:
        if any(_overlaps(reference, known) for known in emitted):
            continue
        cells, complete, merged, hidden = _source_range(reference, regions)
        if len(cells) >= 4:
            reference = _trimmed_range(reference, cells, complete)
            emitted.append(reference)
            yield reference, cells, complete, merged, hidden, "schema"
    all_cells = {address: cell for _, cells in regions for address, cell in cells.items()}
    hidden_rows = {number for region, _ in regions for number in region.hidden_rows}
    merged = {span for region, _ in regions for span in region.merged_ranges}
    for reference in report_ranges(all_cells, hidden_rows, merged):
        if any(_overlaps(reference, known) for known in emitted):
            continue
        cells, complete, merged, hidden = _source_range(reference, regions)
        if not complete:
            continue  # A sample-inferred bottom is not an original population boundary.
        emitted.append(reference)
        yield reference, cells, complete, merged, hidden, "report"
    for region, cells in regions:
        reference = f"{region.start_cell}:{region.end_cell}"
        if any(_overlaps(reference, known) for known in emitted):
            continue
        segments = _row_segments(reference, cells, region.hidden_rows) if _complete(region) else [(reference, cells)]
        for segment, segment_cells in segments:
            _, top, _, bottom = range_boundaries(segment)
            yield (segment, segment_cells, _complete(region),
                   region.merged_ranges,
                   frozenset(row for row in region.hidden_rows if top <= row <= bottom), "region")


def _source_range(reference, regions):
    bounds = range_boundaries(reference)
    cells, complete, merged, hidden = {}, True, [], set()
    for region, values in regions:
        selected = {key: value for key, value in values.items() if _inside(key, bounds)}
        if selected:
            cells.update(selected)
            complete = complete and _complete(region)
            merged.extend(region.merged_ranges)
            hidden.update(row for row in region.hidden_rows if bounds[1] <= row <= bounds[3])
            for span in region.merged_ranges:
                left, top, right, bottom = range_boundaries(span)
                if left == right and top < bounds[1] <= bottom and bounds[0] <= left <= bounds[2]:
                    address = f"{get_column_letter(left)}{top}"
                    if address in values:
                        cells[address] = values[address]
    return cells, complete, merged, frozenset(hidden)


def _complete(region):
    query_complete = getattr(region, "query_complete", None)
    return region.analysis_complete if query_complete is None else query_complete


def _row_segments(reference, cells, hidden_rows):
    left, top, right, bottom = range_boundaries(reference)
    rows = sorted({coordinate_to_tuple(address)[0] for address in cells})
    groups = []
    for row in rows:
        gap = range(groups[-1][-1] + 1, row) if groups else ()
        if not groups or any(number not in hidden_rows for number in gap):
            groups.append([])
        groups[-1].append(row)
    for group in groups:
        if len(group) < 2:
            continue
        start, end = group[0], group[-1]
        if group is groups[0] and all(row in hidden_rows for row in range(top, start)):
            start = top
        if group is groups[-1] and all(row in hidden_rows for row in range(end + 1, bottom + 1)):
            end = bottom
        span = f"{get_column_letter(left)}{start}:{get_column_letter(right)}{end}"
        yield span, {key: value for key, value in cells.items()
                     if start <= coordinate_to_tuple(key)[0] <= end}


def _inside(address, bounds):
    row, column = coordinate_to_tuple(address)
    left, top, right, bottom = bounds
    return left <= column <= right and top <= row <= bottom


def _overlaps(first, second):
    a, b, c, d = range_boundaries(first)
    e, f, g, h = range_boundaries(second)
    return a <= g and e <= c and b <= h and f <= d


def _trimmed_range(reference, cells, complete=True):
    left, top, right, bottom = range_boundaries(reference)
    top = leaf_header_row(cells, left, top, right, bottom)
    bottom = min(bottom, max(coordinate_to_tuple(key)[0] for key in cells)) if complete else bottom
    return f"{get_column_letter(left)}{top}:{get_column_letter(right)}{bottom}"


def table_context(sheet, reference, cells):
    left, top, right, _ = range_boundaries(reference)
    result = []
    for number in range(max(1, top - 3), top):
        for column in range(left, right + 1):
            address = f"{get_column_letter(column)}{number}"
            cell = cells.get(address, {})
            value = cell_value(cell)
            if cell.get("bold") and isinstance(value, str) and value.strip():
                result.append((f"{sheet}!{address}", value.strip()[:250]))
    return tuple(result[:12])
