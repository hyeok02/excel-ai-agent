from datetime import date, datetime, time
from decimal import Decimal

from openpyxl.worksheet.worksheet import Worksheet

from app.services.workbook_details.models import CellValue


def json_value(value: object) -> CellValue:
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, (date, datetime, time)):
        return value.isoformat()
    if isinstance(value, Decimal):
        return float(value)
    return str(value)


def string_or_none(value: object) -> str | None:
    return str(value) if value is not None else None


def is_merged_cell(worksheet: Worksheet, coordinate: str) -> bool:
    return any(coordinate in merged_range for merged_range in worksheet.merged_cells.ranges)


def intersecting_merged_ranges(
    worksheet: Worksheet,
    min_row: int,
    max_row: int,
    min_column: int,
    max_column: int,
) -> list[str]:
    matches = []
    for merged_range in worksheet.merged_cells.ranges:
        if (
            merged_range.max_row >= min_row
            and merged_range.min_row <= max_row
            and merged_range.max_col >= min_column
            and merged_range.min_col <= max_column
        ):
            matches.append(str(merged_range))
            if len(matches) == 20:
                break
    return matches


def cell_fill_color(cell: object) -> str | None:
    fill = getattr(cell, "fill", None)
    if getattr(fill, "fill_type", None) is None:
        return None
    color = getattr(fill, "fgColor", None)
    color_type = getattr(color, "type", None)
    value = getattr(color, color_type, None) if color_type else None
    return str(value) if value not in (None, "00000000", "000000") else None
