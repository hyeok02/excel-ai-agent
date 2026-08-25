from openpyxl.utils import range_boundaries
from openpyxl.worksheet.worksheet import Worksheet

from app.services.region_detector import CellRegion
from app.services.workbook_details.cell_values import intersecting_merged_ranges
from app.services.workbook_details.headers import header_paths, region_title
from app.services.workbook_details.models import RegionSummary
from app.services.workbook_details.snapshots import snapshot_range

REGION_PREVIEW_ROWS = 8
REGION_PREVIEW_COLUMNS = 8


def summarize_regions(
    worksheet: Worksheet,
    regions: list[CellRegion],
    value_worksheet: Worksheet | None = None,
) -> list[RegionSummary]:
    summaries: list[RegionSummary] = []
    for region in regions:
        min_column, min_row, max_column, max_row = range_boundaries(
            f"{region.start_cell}:{region.end_cell}"
        )
        preview_max_row = min(max_row, min_row + REGION_PREVIEW_ROWS - 1)
        preview_max_column = min(
            max_column, min_column + REGION_PREVIEW_COLUMNS - 1
        )
        semantic_role = region.semantic.role if region.semantic else None
        summaries.append(
            RegionSummary(
                start_cell=region.start_cell,
                end_cell=region.end_cell,
                cell_count=region.cell_count,
                title=region_title(
                    worksheet, min_row, max_row, min_column, max_column
                ),
                row_count=max_row - min_row + 1,
                column_count=max_column - min_column + 1,
                merged_ranges=intersecting_merged_ranges(
                    worksheet, min_row, max_row, min_column, max_column
                ),
                header_paths=header_paths(
                    worksheet,
                    min_row,
                    max_row,
                    min_column,
                    max_column,
                    semantic_role,
                ),
                preview_rows=snapshot_range(
                    worksheet,
                    value_worksheet,
                    min_row,
                    preview_max_row,
                    min_column,
                    preview_max_column,
                    region.semantic,
                ),
                is_truncated=(
                    preview_max_row < max_row or preview_max_column < max_column
                ),
                semantic=region.semantic,
            )
        )
    return summaries
