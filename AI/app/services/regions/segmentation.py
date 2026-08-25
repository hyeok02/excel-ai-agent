from openpyxl.worksheet.worksheet import Worksheet

from app.services.regions.classification import (
    classify,
    explicit_role,
    fallback_role,
    is_total_row,
)
from app.services.regions.header_detection import (
    SingleRowHeaderDetection,
    detect_single_row_header,
)
from app.services.regions.models import RegionBounds
from app.services.regions.table_segmentation import (
    context_row_segments,
    legacy_table_segments,
)
from app.services.regions.utils import sub_bounds
from app.services.semantic_models import SemanticClassification, SemanticRole


def segment_and_classify(
    worksheet: Worksheet,
    bounds: RegionBounds,
    sheet_role: str | None,
) -> list[tuple[RegionBounds, SemanticClassification]]:
    explicit = explicit_role(worksheet, bounds, sheet_role)
    if explicit is not None:
        return [(bounds, classify(worksheet, bounds, explicit))]

    header = detect_single_row_header(worksheet, bounds)
    if header is not None:
        return _single_header_segments(worksheet, bounds, sheet_role, header)

    table_segments = legacy_table_segments(worksheet, bounds)
    if table_segments:
        return [
            (segment, classify(worksheet, segment, role))
            for segment, role in table_segments
        ]

    row_segments = context_row_segments(worksheet, bounds, sheet_role)
    if len(row_segments) > 1:
        return [
            (segment, classify(worksheet, segment, role))
            for segment, role in row_segments
        ]
    role = fallback_role(worksheet, bounds, sheet_role)
    return [(bounds, classify(worksheet, bounds, role))]


def _single_header_segments(
    worksheet: Worksheet,
    bounds: RegionBounds,
    sheet_role: str | None,
    header: SingleRowHeaderDetection,
) -> list[tuple[RegionBounds, SemanticClassification]]:
    results = _leading_segments(worksheet, bounds, sheet_role, header.row)
    header_bounds = sub_bounds(bounds, header.row, header.row)
    results.append(
        (
            header_bounds,
            classify(
                worksheet,
                header_bounds,
                SemanticRole.HEADER,
                confidence=header.confidence,
                extra_reasons=(header.reason,),
            ),
        )
    )

    total_start = bounds.max_row + 1
    for row in range(bounds.max_row, header.row, -1):
        if is_total_row(worksheet, bounds, row):
            total_start = row
        else:
            break
    data_end = total_start - 1
    if header.row + 1 <= data_end:
        data_bounds = sub_bounds(bounds, header.row + 1, data_end)
        results.append((data_bounds, classify(worksheet, data_bounds, SemanticRole.DATA)))
    if total_start <= bounds.max_row:
        total_bounds = sub_bounds(bounds, total_start, bounds.max_row)
        results.append((total_bounds, classify(worksheet, total_bounds, SemanticRole.TOTAL)))
    return results


def _leading_segments(
    worksheet: Worksheet,
    bounds: RegionBounds,
    sheet_role: str | None,
    header_row: int,
) -> list[tuple[RegionBounds, SemanticClassification]]:
    if header_row == bounds.min_row:
        return []
    leading = sub_bounds(bounds, bounds.min_row, header_row - 1)
    segments = context_row_segments(worksheet, leading, sheet_role)
    if not segments:
        role = explicit_role(worksheet, leading, sheet_role) or fallback_role(
            worksheet, leading, sheet_role
        )
        segments = [(leading, role)]
    return [(segment, classify(worksheet, segment, role)) for segment, role in segments]
