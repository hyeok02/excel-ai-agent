from dataclasses import replace

from openpyxl.utils import range_boundaries
from openpyxl.worksheet.worksheet import Worksheet

from app.services.region_detector import CellRegion
from app.services.provenance import (
    build_provenance,
    evidence_from_reasons,
    evidence_from_reference,
)
from app.services.semantic_models import SemanticClassification
from app.services.workbook_details.analysis_samples import (
    MAX_ANALYSIS_SHEET_CELLS,
    analysis_cell_index,
    collect_analysis_sample,
)
from app.services.workbook_details.cell_values import intersecting_merged_ranges
from app.services.workbook_details.headers import header_paths, region_title
from app.services.workbook_details.models import RegionSummary
from app.services.workbook_details.snapshots import snapshot_range
from app.services.workbook_details.visibility import hidden_columns, hidden_rows

REGION_PREVIEW_ROWS = 8
REGION_PREVIEW_COLUMNS = 8


def summarize_regions(
    worksheet: Worksheet,
    regions: list[CellRegion],
    value_worksheet: Worksheet | None = None,
) -> list[RegionSummary]:
    summaries: list[RegionSummary] = []
    remaining_analysis_cells = MAX_ANALYSIS_SHEET_CELLS
    cell_index = analysis_cell_index(worksheet)
    cached_cells = (
        getattr(value_worksheet, "_cells", {})
        if value_worksheet is not None
        else {}
    )
    for region in regions:
        min_column, min_row, max_column, max_row = range_boundaries(
            f"{region.start_cell}:{region.end_cell}"
        )
        preview_max_row = min(max_row, min_row + REGION_PREVIEW_ROWS - 1)
        preview_max_column = min(
            max_column, min_column + REGION_PREVIEW_COLUMNS - 1
        )
        semantic_role = region.semantic.role if region.semantic else None
        semantic = _semantic_with_provenance(worksheet.title, region)
        region_hidden_rows = hidden_rows(worksheet, min_row, max_row)
        region_hidden_columns = hidden_columns(
            worksheet, min_column, max_column
        )
        analysis_rows, analysis_complete = collect_analysis_sample(
            worksheet, value_worksheet,
            (min_column, min_row, max_column, max_row), remaining_analysis_cells,
            set(region_hidden_rows), set(region_hidden_columns),
            cell_index, cached_cells,
        )
        analysis_cell_count = sum(len(row) for row in analysis_rows)
        remaining_analysis_cells -= analysis_cell_count
        summaries.append(
            RegionSummary(
                start_cell=region.start_cell,
                end_cell=region.end_cell,
                cell_count=region.cell_count,
                title=region_title(
                    worksheet, min_row, max_row, min_column, max_column,
                    value_worksheet,
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
                semantic=semantic,
                analysis_rows=analysis_rows,
                analysis_complete=analysis_complete,
                hidden_rows=region_hidden_rows,
                hidden_columns=region_hidden_columns,
            )
        )
    return summaries

def _semantic_with_provenance(
    sheet_name: str, region: CellRegion
) -> SemanticClassification | None:
    if region.semantic is None:
        return None
    evidence = evidence_from_reasons(sheet_name, region.semantic.reasons)
    if not evidence:
        evidence = (
            evidence_from_reference(
                sheet_name,
                f"{region.start_cell}:{region.end_cell}",
                f"{region.semantic.role.value} 역할로 분류된 셀 영역",
            ),
        )
    return replace(
        region.semantic,
        provenance=build_provenance(
            "region_semantic_classifier",
            region.semantic.confidence,
            evidence,
        ),
    )
