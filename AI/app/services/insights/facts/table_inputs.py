"""Bounded, region-preserving table input for deterministic narratives."""
from typing import Any, Iterable


MAX_TABLE_REGIONS = 24
MAX_ROWS_PER_REGION = 48
MAX_LEGACY_ROWS = 48
MAX_TABLE_CELLS = 2048


def build_table_regions(regions: list[dict[str, Any]]) -> list[dict[str, object]]:
    tables = []
    remaining = MAX_TABLE_CELLS
    for region in regions[:MAX_TABLE_REGIONS]:
        rows = []
        for row in _rows(region)[:MAX_ROWS_PER_REGION]:
            if len(row) > remaining:
                break
            rows.append(row)
            remaining -= len(row)
        if not rows:
            continue
        semantic = region.get("semantic")
        role = semantic.get("role") if isinstance(semantic, dict) else None
        title = region.get("title")
        tables.append({
            "title": title,
            "title_cell": _title_cell(rows, title),
            "role": role,
            "start_cell": region.get("start_cell"),
            "end_cell": region.get("end_cell"),
            "rows": rows,
        })
        if remaining == 0:
            break
    return tables


def legacy_table_rows(tables: list[dict[str, object]]) -> list[list[dict]]:
    return [
        row
        for table in tables
        for row in table.get("rows", [])
    ][:MAX_LEGACY_ROWS]


def narrative_regions(facts: dict[str, object]) -> Iterable[dict[str, object]]:
    tables = facts.get("table_regions")
    if isinstance(tables, list) and tables:
        yield from (table for table in tables if isinstance(table, dict))
        return
    rows = facts.get("table_rows")
    if isinstance(rows, list) and rows:
        yield {"title": None, "role": None, "rows": rows}


def _rows(region: dict[str, Any]) -> list[list[dict]]:
    source = region.get("analysis_rows") or region.get("preview_rows", [])
    result = []
    for row in source:
        cells = []
        for cell in row:
            raw = cell.get("cached_value") if cell.get("formula") else cell.get("value")
            address = cell.get("address")
            if raw in (None, "") or not address or len(str(raw)) > 600:
                continue
            cells.append({
                "cell": address,
                "value": raw,
                "number_format": cell.get("number_format"),
            })
        if cells:
            result.append(cells)
    return result


def _title_cell(rows, title):
    if title in (None, ""):
        return None
    expected = " ".join(str(title).split())
    return next(
        (cell for row in rows for cell in row
         if " ".join(str(cell.get("value", "")).split()) == expected),
        None,
    )
