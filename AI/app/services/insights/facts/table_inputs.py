"""Bounded, region-preserving table input for deterministic narratives."""
from typing import Any, Iterable

from app.services.insights.facts.region_rows import normalized_region_rows


MAX_TABLE_REGIONS = 24
MAX_LEGACY_ROWS = 48
MAX_TABLE_CELLS = 2048
MAX_ROWS_PER_REGION = MAX_TABLE_CELLS


def build_table_regions(regions: list[dict[str, Any]]) -> list[dict[str, object]]:
    tables = []
    remaining = MAX_TABLE_CELLS
    for region in regions[:MAX_TABLE_REGIONS]:
        source_rows, analysis_complete = normalized_region_rows(region)
        rows = []
        clipped = len(source_rows) > MAX_ROWS_PER_REGION
        for row in source_rows[:MAX_ROWS_PER_REGION]:
            if len(row) > remaining:
                clipped = True
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
            "analysis_complete": analysis_complete,
            "rows_complete": analysis_complete and not clipped,
            "hidden_columns": list(region.get("hidden_columns", [])),
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
        for table in tables:
            if not isinstance(table, dict):
                continue
            if table.get("rows_complete") is False:
                yield {**table, "rows": []}
            else:
                yield table
        return
    rows = facts.get("table_rows")
    if isinstance(rows, list) and rows:
        yield {"title": None, "role": None, "rows": rows}

def _title_cell(rows, title):
    if title in (None, ""):
        return None
    expected = " ".join(str(title).split())
    return next(
        (cell for row in rows for cell in row
         if " ".join(str(cell.get("value", "")).split()) == expected),
        None,
    )
