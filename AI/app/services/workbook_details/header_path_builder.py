from collections.abc import Iterable
from openpyxl.utils import get_column_letter
from openpyxl.worksheet.worksheet import Worksheet

from app.services.workbook_details.merged_headers import resolved_header_rows
from app.services.workbook_details.models import HeaderPathSummary


def build_header_paths(
    worksheet: Worksheet,
    min_row: int,
    max_row: int,
    min_column: int,
    max_column: int,
) -> list[HeaderPathSummary]:
    rows = resolved_header_rows(
        worksheet,
        min_row,
        max_row,
        min_column,
        max_column,
    )
    paths = []
    for index, column in enumerate(range(min_column, max_column + 1)):
        labels = normalize_path(row[index] for row in rows)
        if labels:
            paths.append(
                HeaderPathSummary(column=get_column_letter(column), labels=labels)
            )
    return paths


def normalize_path(labels: Iterable[str | None]) -> list[str]:
    path: list[str] = []
    for label in labels:
        if label is None:
            continue
        normalized = " ".join(label.split())
        if normalized and (not path or path[-1] != normalized):
            path.append(normalized)
    return path
