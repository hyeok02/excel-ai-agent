from openpyxl.worksheet.worksheet import Worksheet

from app.services.semantic_models import SemanticRole
from app.services.workbook_details.header_labels import header_label
from app.services.workbook_details.header_path_builder import build_header_paths
from app.services.workbook_details.models import HeaderPathSummary


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
    return build_header_paths(
        worksheet,
        min_row,
        max_row,
        min_column,
        max_column,
    )
