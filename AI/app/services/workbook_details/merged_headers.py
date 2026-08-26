from openpyxl.worksheet.worksheet import Worksheet

from app.services.regions.utils import merged_anchor
from app.services.workbook_details.header_labels import header_label


def resolved_header_rows(
    worksheet: Worksheet,
    min_row: int,
    max_row: int,
    min_column: int,
    max_column: int,
) -> list[list[str | None]]:
    return [
        [
            resolved_header_label(worksheet, row, column)
            for column in range(min_column, max_column + 1)
        ]
        for row in range(min_row, max_row + 1)
    ]


def resolved_header_label(
    worksheet: Worksheet,
    row: int,
    column: int,
) -> str | None:
    value = worksheet.cell(row=row, column=column).value
    label = header_label(value)
    if label is not None:
        return label
    anchor = merged_anchor(worksheet, row, column)
    if anchor is None:
        return None
    return header_label(worksheet.cell(row=anchor[0], column=anchor[1]).value)
