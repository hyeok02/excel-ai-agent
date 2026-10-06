"""Hidden row and column metadata for a worksheet region."""
from openpyxl.utils import column_index_from_string, get_column_letter
from openpyxl.worksheet.worksheet import Worksheet


def hidden_rows(worksheet: Worksheet, min_row: int, max_row: int) -> list[int]:
    return sorted(
        row
        for row, dimension in worksheet.row_dimensions.items()
        if min_row <= row <= max_row and bool(dimension.hidden)
    )


def hidden_columns(
    worksheet: Worksheet, min_column: int, max_column: int
) -> list[str]:
    hidden: set[int] = set()
    for key, dimension in worksheet.column_dimensions.items():
        if not dimension.hidden:
            continue
        start = dimension.min or column_index_from_string(str(key))
        end = dimension.max or start
        hidden.update(range(max(min_column, start), min(max_column, end) + 1))
    return [get_column_letter(column) for column in sorted(hidden)]
