"""Bounded source samples independent of the small visual table preview."""
from openpyxl.worksheet.worksheet import Worksheet

from app.services.workbook_details.cell_values import json_value, string_or_none
from app.services.workbook_details.models import CellValue

MAX_ANALYSIS_REGION_CELLS = 512
MAX_ANALYSIS_SHEET_CELLS = 2048


def collect_analysis_rows(
    worksheet: Worksheet,
    value_worksheet: Worksheet | None,
    bounds: tuple[int, int, int, int],
    remaining_cells: int,
) -> list[list[dict[str, CellValue]]]:
    """Return a whole small region, or [] so callers reuse the existing preview.

    The rectangular area, including empty cells, counts against both limits.
    Large/sparse regions are rejected before accessing any cells; no second
    unbounded worksheet scan or duplicate semantic/style snapshots are needed.
    """
    min_column, min_row, max_column, max_row = bounds
    cell_count = (max_column - min_column + 1) * (max_row - min_row + 1)
    if cell_count <= 0 or cell_count > min(MAX_ANALYSIS_REGION_CELLS, remaining_cells):
        return []
    return [
        [
            _analysis_cell(
                worksheet.cell(row=row, column=column),
                value_worksheet.cell(row=row, column=column)
                if value_worksheet is not None else None,
            )
            for column in range(min_column, max_column + 1)
        ]
        for row in range(min_row, max_row + 1)
    ]


def _analysis_cell(cell: object, value_cell: object | None) -> dict[str, CellValue]:
    raw_value = getattr(cell, "value", None)
    is_formula = getattr(cell, "data_type", None) == "f" and isinstance(raw_value, str)
    return {
        "address": str(getattr(cell, "coordinate")),
        "value": None if is_formula else json_value(raw_value),
        "formula": raw_value if is_formula else None,
        "cached_value": json_value(getattr(value_cell, "value", None)) if is_formula else None,
        "number_format": string_or_none(getattr(cell, "number_format", None)),
    }
