from collections import deque
from dataclasses import dataclass

from openpyxl.utils import get_column_letter
from openpyxl.worksheet.worksheet import Worksheet


@dataclass(frozen=True)
class CellRegion:
    start_cell: str
    end_cell: str
    cell_count: int


def detect_regions(worksheet: Worksheet) -> list[CellRegion]:
    populated_cells = {
        (cell.row, cell.column)
        for cell in worksheet._cells.values()
        if _is_populated(cell.value)
    }
    visited: set[tuple[int, int]] = set()
    regions: list[CellRegion] = []

    for start in sorted(populated_cells):
        if start in visited:
            continue

        queue = deque([start])
        visited.add(start)
        cells: list[tuple[int, int]] = []

        while queue:
            row, column = queue.popleft()
            cells.append((row, column))

            for neighbor in (
                (row - 1, column),
                (row + 1, column),
                (row, column - 1),
                (row, column + 1),
            ):
                if neighbor in populated_cells and neighbor not in visited:
                    visited.add(neighbor)
                    queue.append(neighbor)

        min_row = min(row for row, _ in cells)
        max_row = max(row for row, _ in cells)
        min_column = min(column for _, column in cells)
        max_column = max(column for _, column in cells)
        regions.append(
            CellRegion(
                start_cell=_coordinate(min_row, min_column),
                end_cell=_coordinate(max_row, max_column),
                cell_count=len(cells),
            )
        )

    return regions


def _is_populated(value: object) -> bool:
    return value is not None and not (isinstance(value, str) and not value.strip())


def _coordinate(row: int, column: int) -> str:
    return f"{get_column_letter(column)}{row}"
