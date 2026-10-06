"""Bounded source samples independent of the small visual table preview."""
from openpyxl.utils import get_column_letter
from openpyxl.worksheet.worksheet import Worksheet

from app.services.workbook_details.cell_values import json_value, string_or_none
from app.services.workbook_details.models import CellValue

MAX_ANALYSIS_REGION_CELLS = 2048
MAX_ANALYSIS_SHEET_CELLS = 2048
MAX_ANALYSIS_SCAN_CELLS = 50_000


def analysis_cell_index(worksheet: Worksheet) -> dict[int, list[tuple[int, object]]]:
    index: dict[int, list[tuple[int, object]]] = {}
    for (row, column), cell in getattr(worksheet, "_cells", {}).items():
        index.setdefault(row, []).append((column, cell))
    return {
        row: sorted(index[row], key=lambda item: item[0])
        for row in sorted(index)
    }


def collect_analysis_rows(
    worksheet: Worksheet,
    value_worksheet: Worksheet | None,
    bounds: tuple[int, int, int, int],
    remaining_cells: int,
) -> list[list[dict[str, CellValue]]]:
    rows, _ = collect_analysis_sample(
        worksheet, value_worksheet, bounds, remaining_cells
    )
    return rows


def collect_analysis_sample(
    worksheet: Worksheet,
    value_worksheet: Worksheet | None,
    bounds: tuple[int, int, int, int],
    remaining_cells: int,
    hidden_rows: set[int] | None = None,
    hidden_columns: set[str] | None = None,
    cell_index: dict[int, list[tuple[int, object]]] | None = None,
    cached_cells: dict[tuple[int, int], object] | None = None,
) -> tuple[list[list[dict[str, CellValue]]], bool]:
    """Collect a complete dense or sparse sample within fixed scan/storage caps."""
    min_column, min_row, max_column, max_row = bounds
    limit = min(MAX_ANALYSIS_REGION_CELLS, remaining_cells)
    hidden_rows = hidden_rows or set()
    hidden_columns = {str(column).upper() for column in (hidden_columns or set())}
    if max_column < min_column or max_row < min_row or limit <= 0:
        return [], False
    cell_index = cell_index or analysis_cell_index(worksheet)
    if cached_cells is None:
        cached_cells = (
            getattr(value_worksheet, "_cells", {})
            if value_worksheet is not None else {}
        )
    rows, values, stored, scanned = [], [], 0, 0
    for row, cells in cell_index.items():
        if row < min_row:
            continue
        if row > max_row:
            break
        if row in hidden_rows:
            continue
        for column, cell in cells:
            if not min_column <= column <= max_column:
                continue
            if _column_name(column) in hidden_columns:
                continue
            scanned += 1
            if scanned > MAX_ANALYSIS_SCAN_CELLS:
                return [], False
            value = _analysis_cell(cell, cached_cells.get((row, column)))
            if not _populated(value):
                continue
            values.append(value)
            stored += 1
            if stored > limit:
                return [], False
        if values:
            rows.append(values)
            values = []
    return rows, True


def _column_name(column: int) -> str:
    return get_column_letter(column)


def _populated(cell: dict[str, CellValue]) -> bool:
    value = cell.get("cached_value") if cell.get("formula") else cell.get("value")
    return cell.get("formula") is not None or value not in (None, "")


def _analysis_cell(cell: object, value_cell: object | None) -> dict[str, CellValue]:
    raw_value = getattr(cell, "value", None)
    is_formula = getattr(cell, "data_type", None) == "f" and isinstance(raw_value, str)
    return {
        "address": str(getattr(cell, "coordinate")),
        "value": None if is_formula else json_value(raw_value),
        "formula": raw_value if is_formula else None,
        "cached_value": json_value(getattr(value_cell, "value", None)) if is_formula else None,
        "number_format": string_or_none(getattr(cell, "number_format", None)),
        "bold": bool(getattr(getattr(cell, "font", None), "bold", False)),
    }
