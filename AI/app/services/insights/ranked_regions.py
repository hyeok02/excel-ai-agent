"""Join a structured header to only its immediately adjacent data region."""
from openpyxl.utils.cell import coordinate_from_string

from app.services.insights.narrative_values import finite
from app.services.insights.table_schema import column, detect_schema


def ranked_regions(regions):
    regions = list(regions)
    results = list(regions)
    for header in regions:
        detected = detect_schema(header.get("rows", []))
        bounds = _bounds(header)
        if not detected or not bounds:
            continue
        header_index, schema, headers = detected
        if _has_records(header.get("rows", []), header_index, schema):
            continue
        required = {value for value in schema.values() if isinstance(value, int)}
        for body in regions:
            body_bounds = _bounds(body)
            if (not body_bounds or body_bounds[0] != bounds[1] + 1
                    or not required <= _columns(body)
                    or not _first_record(body, schema)):
                continue
            rows = [*header.get("rows", []), *body.get("rows", [])]
            if not _has_records(rows, header_index, schema):
                continue
            title, title_cell = _title(header, headers)
            results.append({
                "title": title, "title_cell": title_cell,
                "role": body.get("role"), "rows": rows,
            })
            break
    return results


def _has_records(rows, header_index, schema):
    for row in rows[header_index + 1:]:
        if _record_row(row, schema):
            return True
    return False


def _record_row(row, schema):
    if not row:
        return False
    mapped = {column(cell): cell for cell in row}
    share = mapped.get(schema["share"])
    label_role = "name" if "name" in schema else "label"
    label = mapped.get(schema.get(label_role, -1))
    rank = mapped.get(schema.get("rank", -1))
    return bool(share and finite(share.get("value")) and label
                and isinstance(label.get("value"), str)
                and ("rank" not in schema or rank and finite(rank.get("value"))))


def _first_record(region, schema):
    rows = region.get("rows", [])
    return bool(rows) and _record_row(rows[0], schema)


def _title(region, headers):
    title, cell = region.get("title"), region.get("title_cell")
    if not title or not isinstance(cell, dict):
        return None, None
    normalized = " ".join(str(title).split()).casefold()
    header_values = {" ".join(str(value).split()).casefold() for value in headers.values()}
    return (None, None) if normalized in header_values else (title, cell)


def _bounds(region):
    rows = [coordinate_from_string(cell["cell"])[1]
            for row in region.get("rows", []) for cell in row]
    return (min(rows), max(rows)) if rows else None


def _columns(region):
    return {column(cell) for row in region.get("rows", []) for cell in row}
