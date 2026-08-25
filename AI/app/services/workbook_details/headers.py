from datetime import date, datetime

from openpyxl.utils import get_column_letter
from openpyxl.worksheet.worksheet import Worksheet

from app.services.semantic_models import SemanticRole
from app.services.workbook_details.cell_values import is_merged_cell
from app.services.workbook_details.models import HeaderPathSummary

HEADER_SCAN_ROWS = 4
HEADER_SCAN_COLUMNS = 12


def region_title(
    worksheet: Worksheet,
    min_row: int,
    max_row: int,
    min_column: int,
    max_column: int,
) -> str | None:
    for row in worksheet.iter_rows(
        min_row=min_row,
        max_row=min(max_row, min_row + 3),
        min_col=min_column,
        max_col=max_column,
    ):
        for cell in row:
            label = header_label(cell.value)
            if label is not None:
                return label
    return None


def header_paths(
    worksheet: Worksheet,
    min_row: int,
    max_row: int,
    min_column: int,
    max_column: int,
    semantic_role: SemanticRole | None,
) -> list[HeaderPathSummary]:
    if semantic_role is not SemanticRole.HEADER:
        return []
    header_max_row = min(max_row, min_row + HEADER_SCAN_ROWS - 1)
    column_max = min(max_column, min_column + HEADER_SCAN_COLUMNS - 1)
    propagated_rows = _propagated_header_rows(
        worksheet,
        min_row,
        header_max_row,
        min_column,
        column_max,
    )
    paths = []
    for index, column_number in enumerate(range(min_column, column_max + 1)):
        labels = []
        for row_labels in propagated_rows:
            label = row_labels[index]
            if label is not None and (not labels or labels[-1] != label):
                labels.append(label)
        if labels:
            paths.append(
                HeaderPathSummary(column=get_column_letter(column_number), labels=labels)
            )
    return paths


def _propagated_header_rows(
    worksheet: Worksheet,
    min_row: int,
    max_row: int,
    min_column: int,
    max_column: int,
) -> list[list[str | None]]:
    propagated = []
    for row_number in range(min_row, max_row + 1):
        labels = []
        previous_label = None
        for column_number in range(min_column, max_column + 1):
            cell = worksheet.cell(row=row_number, column=column_number)
            label = header_label(cell.value)
            if label is None and is_merged_cell(worksheet, cell.coordinate):
                label = previous_label
            if label is not None:
                previous_label = label
            labels.append(label)
        propagated.append(labels)
    return propagated


def header_label(value: object) -> str | None:
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return str(value)
    if not isinstance(value, str):
        return None
    normalized = value.strip()
    if not normalized or normalized.startswith("=") or len(normalized) > 120:
        return None
    return normalized
