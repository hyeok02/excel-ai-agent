"""Project region samples onto cells that are visible to workbook readers."""
from typing import Any

from openpyxl.utils.cell import coordinate_from_string


def visible_region_rows(
    region: dict[str, Any],
) -> tuple[list[list[dict[str, Any]]], bool]:
    analysis = region.get("analysis_rows")
    if isinstance(analysis, list) and analysis:
        source = analysis
        complete = bool(region.get("analysis_complete", True))
    else:
        source = region.get("preview_rows", [])
        declared = region.get("analysis_complete")
        complete = (
            not bool(region.get("is_truncated", False))
            if declared is None else bool(declared)
        )
    hidden_rows = _integers(region.get("hidden_rows", []))
    hidden_columns = {
        str(column).upper() for column in region.get("hidden_columns", [])
    }
    rows = []
    for row in source if isinstance(source, list) else []:
        visible = [
            cell for cell in row
            if isinstance(cell, dict)
            and not _hidden(cell.get("address"), hidden_rows, hidden_columns)
        ]
        if visible:
            rows.append(visible)
    return rows, complete


def normalized_region_rows(
    region: dict[str, Any],
) -> tuple[list[list[dict[str, object]]], bool]:
    source, complete = visible_region_rows(region)
    rows = []
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
                "bold": bool(cell.get("bold")),
            })
        if cells:
            rows.append(cells)
    return rows, complete


def _hidden(address, hidden_rows, hidden_columns) -> bool:
    if not address:
        return False
    try:
        column, row = coordinate_from_string(str(address).replace("$", ""))
    except ValueError:
        return False
    return row in hidden_rows or column.upper() in hidden_columns


def _integers(values) -> set[int]:
    result = set()
    for value in values:
        try:
            result.add(int(value))
        except (TypeError, ValueError):
            continue
    return result
