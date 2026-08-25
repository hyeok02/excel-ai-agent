from openpyxl.utils import range_boundaries
from openpyxl.worksheet.worksheet import Worksheet

from app.services.workbook_details.models import TableSummary
from app.services.workbook_details.snapshots import snapshot_range

TABLE_PREVIEW_ROWS = 8
TABLE_PREVIEW_COLUMNS = 12


def summarize_tables(
    worksheet: Worksheet,
    value_worksheet: Worksheet | None = None,
) -> list[TableSummary]:
    summaries: list[TableSummary] = []
    for table in worksheet.tables.values():
        min_column, min_row, max_column, max_row = range_boundaries(table.ref)
        preview_max_row = min(max_row, min_row + TABLE_PREVIEW_ROWS - 1)
        preview_max_column = min(
            max_column, min_column + TABLE_PREVIEW_COLUMNS - 1
        )
        summaries.append(
            TableSummary(
                name=table.name,
                display_name=table.displayName,
                reference=table.ref,
                headers=[column.name for column in table.tableColumns],
                row_count=max_row - min_row + 1,
                column_count=max_column - min_column + 1,
                preview_rows=snapshot_range(
                    worksheet,
                    value_worksheet,
                    min_row,
                    preview_max_row,
                    min_column,
                    preview_max_column,
                ),
                is_truncated=(
                    preview_max_row < max_row or preview_max_column < max_column
                ),
            )
        )
    return summaries
