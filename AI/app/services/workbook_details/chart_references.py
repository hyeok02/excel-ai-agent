from openpyxl.utils import range_boundaries
from openpyxl.workbook.workbook import Workbook

from app.services.workbook_details.cell_values import json_value
from app.services.workbook_details.chart_named_references import (
    resolve_named_chart_reference,
)
from app.services.workbook_details.models import CellValue


def resolve_reference_values(
    workbook: Workbook,
    reference: object,
    limit: int,
) -> list[CellValue]:
    if not isinstance(reference, str):
        return []
    normalized = resolve_named_chart_reference(workbook, reference)
    if normalized is None or "!" not in normalized:
        return []

    sheet_token, range_token = normalized.lstrip("=").rsplit("!", 1)
    sheet_name = sheet_token.strip("'").replace("''", "'")
    if sheet_name not in workbook.sheetnames:
        return []
    try:
        min_column, min_row, max_column, max_row = range_boundaries(
            range_token.replace("$", "")
        )
    except ValueError:
        return []

    values: list[CellValue] = []
    worksheet = workbook[sheet_name]
    for row in worksheet.iter_rows(
        min_row=min_row,
        max_row=max_row,
        min_col=min_column,
        max_col=max_column,
    ):
        for cell in row:
            values.append(json_value(cell.value))
            if len(values) == limit:
                return values
    return values
