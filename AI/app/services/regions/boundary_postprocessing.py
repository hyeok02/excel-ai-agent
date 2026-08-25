from openpyxl.worksheet.worksheet import Worksheet

from app.services.regions.models import RegionBounds
from app.services.regions.utils import (
    intersecting_merged_ranges,
    populated_coordinates,
)


def split_isolated_bounds(
    worksheet: Worksheet,
    bounds: list[RegionBounds],
) -> list[RegionBounds]:
    results: list[RegionBounds] = []
    populated = populated_coordinates(worksheet)
    for item in bounds:
        coordinates = {
            cell
            for cell in populated
            if item.min_row <= cell[0] <= item.max_row
            and item.min_column <= cell[1] <= item.max_column
        }
        has_adjacent_cells = any(
            (row + row_offset, column + column_offset) in coordinates
            for row, column in coordinates
            for row_offset, column_offset in ((1, 0), (0, 1))
        )
        should_split = (
            len(coordinates) > 1
            and not has_adjacent_cells
            and not intersecting_merged_ranges(worksheet, item)
        )
        if should_split:
            results.extend(
                RegionBounds(
                    min_row=row,
                    max_row=row,
                    min_column=column,
                    max_column=column,
                    boundary_reasons=item.boundary_reasons,
                )
                for row, column in sorted(coordinates)
            )
        else:
            results.append(item)
    return results
