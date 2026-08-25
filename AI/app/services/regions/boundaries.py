from openpyxl.worksheet.worksheet import Worksheet

from app.services.regions.boundary_groups import (
    boundary_reasons,
    column_groups,
    contiguous_groups,
    shared_merged_heading,
)
from app.services.regions.boundary_postprocessing import split_isolated_bounds
from app.services.regions.models import RegionBounds
from app.services.regions.utils import (
    coordinate,
    formula_count,
)
from app.services.semantic_models import SemanticReason


def detect_base_bounds(
    worksheet: Worksheet,
    populated: set[tuple[int, int]],
) -> list[RegionBounds]:
    occupied = set(populated)
    for merged_range in worksheet.merged_cells.ranges:
        if (merged_range.min_row, merged_range.min_col) not in populated:
            continue
        occupied.update(
            (row, column)
            for row in range(merged_range.min_row, merged_range.max_row + 1)
            for column in range(merged_range.min_col, merged_range.max_col + 1)
        )

    row_groups = contiguous_groups({row for row, _ in occupied})
    results: list[RegionBounds] = []
    for min_row, max_row in row_groups:
        groups = column_groups(occupied, min_row, max_row)
        shared_heading = shared_merged_heading(
            worksheet,
            min_row,
            max_row,
            groups,
        )
        if shared_heading is not None:
            groups = column_groups(occupied, min_row + 1, max_row)

        for min_column, max_column in groups:
            group_rows = [
                row
                for row, column in occupied
                if min_column <= column <= max_column
                and min_row <= row <= max_row
            ]
            group_min_row = min(group_rows)
            group_max_row = max(group_rows)
            reasons = boundary_reasons(
                group_min_row,
                group_max_row,
                min_column,
                max_column,
                len(groups),
                shared_heading,
            )
            results.append(
                RegionBounds(
                    min_row=group_min_row,
                    max_row=group_max_row,
                    min_column=min_column,
                    max_column=max_column,
                    boundary_reasons=reasons,
                )
            )
    return split_isolated_bounds(worksheet, results)


def merge_documentation_bounds(
    worksheet: Worksheet,
    bounds: list[RegionBounds],
) -> list[RegionBounds]:
    if len(bounds) < 2:
        return bounds
    merged: list[RegionBounds] = []
    current = bounds[0]
    for candidate in bounds[1:]:
        gap = candidate.min_row - current.max_row - 1
        overlaps = not (
            candidate.max_column < current.min_column
            or candidate.min_column > current.max_column
        )
        combined = RegionBounds(
            min_row=current.min_row,
            max_row=candidate.max_row,
            min_column=min(current.min_column, candidate.min_column),
            max_column=max(current.max_column, candidate.max_column),
            boundary_reasons=(
                *current.boundary_reasons,
                SemanticReason(
                    code="documentation_flow",
                    message="한 줄 간격의 제목과 안내 본문을 하나의 설명 흐름으로 결합",
                    evidence_cells=(
                        coordinate(current.min_row, current.min_column),
                        coordinate(candidate.max_row, candidate.max_column),
                    ),
                ),
            ),
        )
        if gap <= 1 and overlaps and formula_count(worksheet, combined) == 0:
            current = combined
        else:
            merged.append(current)
            current = candidate
    merged.append(current)
    return merged
