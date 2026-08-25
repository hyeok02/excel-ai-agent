from openpyxl.worksheet.worksheet import Worksheet

from app.services.regions.utils import coordinate, is_populated
from app.services.semantic_models import SemanticReason


def contiguous_groups(values: set[int]) -> list[tuple[int, int]]:
    if not values:
        return []
    sorted_values = sorted(values)
    groups: list[tuple[int, int]] = []
    start = previous = sorted_values[0]
    for value in sorted_values[1:]:
        if value > previous + 1:
            groups.append((start, previous))
            start = value
        previous = value
    groups.append((start, previous))
    return groups


def column_groups(
    occupied: set[tuple[int, int]],
    min_row: int,
    max_row: int,
) -> list[tuple[int, int]]:
    columns = {column for row, column in occupied if min_row <= row <= max_row}
    return contiguous_groups(columns)


def shared_merged_heading(
    worksheet: Worksheet,
    min_row: int,
    max_row: int,
    groups: list[tuple[int, int]],
) -> str | None:
    if min_row == max_row or len(groups) != 1:
        return None
    lower_occupied = {
        (cell.row, cell.column)
        for cell in worksheet._cells.values()
        if min_row < cell.row <= max_row and is_populated(cell.value)
    }
    if len(column_groups(lower_occupied, min_row + 1, max_row)) <= 1:
        return None
    for merged_range in worksheet.merged_cells.ranges:
        if merged_range.min_row == min_row and merged_range.max_row == min_row:
            return str(merged_range)
    return None


def boundary_reasons(
    min_row: int,
    max_row: int,
    min_column: int,
    max_column: int,
    group_count: int,
    shared_heading: str | None,
) -> tuple[SemanticReason, ...]:
    reasons = []
    evidence = tuple(
        dict.fromkeys(
            (
                coordinate(min_row, min_column),
                coordinate(max_row, max_column),
            )
        )
    )
    if min_row > 1:
        reasons.append(
            SemanticReason(
                code="blank_row_boundary",
                message="빈 행을 기준으로 위아래 영역을 분리",
                evidence_cells=evidence,
            )
        )
    if group_count > 1:
        reasons.append(
            SemanticReason(
                code="blank_column_boundary",
                message="빈 열을 기준으로 좌우 영역을 분리",
                evidence_cells=evidence,
            )
        )
    if shared_heading is not None:
        reasons.append(
            SemanticReason(
                code="shared_merged_heading",
                message="공통 병합 제목 아래의 열 묶음을 독립 영역으로 분리",
                evidence_cells=(shared_heading,),
            )
        )
    return tuple(reasons)
