from openpyxl.worksheet.worksheet import Worksheet

from app.services.regions.classification import classify, explicit_role, fallback_role
from app.services.regions.header_segmentation import header_segments
from app.services.regions.hierarchical_header_detection import (
    detect_merged_hierarchical_header,
)
from app.services.regions.header_detection import (
    detect_single_row_header,
)
from app.services.regions.models import RegionBounds
from app.services.regions.table_segmentation import (
    context_row_segments,
    legacy_table_segments,
)
from app.services.semantic_models import SemanticClassification


def segment_and_classify(
    worksheet: Worksheet,
    bounds: RegionBounds,
    sheet_role: str | None,
) -> list[tuple[RegionBounds, SemanticClassification]]:
    explicit = explicit_role(worksheet, bounds, sheet_role)
    if explicit is not None:
        return [(bounds, classify(worksheet, bounds, explicit))]

    hierarchical = detect_merged_hierarchical_header(worksheet, bounds)
    if hierarchical is not None:
        return header_segments(
            worksheet,
            bounds,
            sheet_role,
            hierarchical.start_row,
            hierarchical.end_row,
            hierarchical.confidence,
            hierarchical.reason,
        )

    header = detect_single_row_header(worksheet, bounds)
    if header is not None:
        return header_segments(
            worksheet,
            bounds,
            sheet_role,
            header.row,
            header.row,
            header.confidence,
            header.reason,
        )

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
