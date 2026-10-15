"""Validate every table observation against the original workbook index."""
from openpyxl.utils import coordinate_to_tuple, get_column_letter, range_boundaries


def query_columns(plan, table) -> list[str] | None:
    columns = [column.id for column in table.columns]
    selected = list(dict.fromkeys(plan.column_ids))
    if not set(selected) <= set(columns):
        return None
    if getattr(plan, "column_scope", "selected") == "selected":
        return selected
    identity = set(getattr(plan, "identity_column_ids", []))
    if not identity <= set(columns):
        return None
    for column in identity:
        values = [row.values[column] for row in table.rows]
        if any(value in (None, "") for value in values):
            return None
        if len({(type(value).__name__, value) for value in values}) != len(values):
            return None
    return [column for column in columns if column not in identity]


def validated_table(table, index, needed: set[str]) -> bool:
    if not table.complete:
        return False
    columns = {column.id: column for column in table.columns}
    if not needed <= columns.keys():
        return False
    cells = {cell.address: cell for row in index.rows if row.sheet_name == table.sheet_name
             for cell in row.cells}
    left, top, right, bottom = range_boundaries(table.reference)
    if index.truncated_for({table.sheet_name}):
        cutoff = max((coordinate_to_tuple(address) for address in cells), default=(0, 0))
        if cutoff < (bottom, right):
            return False
    for column in table.columns:
        address = column.header_reference.rpartition("!")[2]
        cell = cells.get(address)
        if cell is None or not isinstance(cell.value, str) or cell.value.strip() != column.header:
            return False
    source_rows = {row.row_number: row for row in table.rows}
    for row in table.rows:
        for column in columns:
            cell = cells.get(f"{column}{row.row_number}")
            actual = cell.value if cell else None
            expected = row.values[column]
            if not _same_value(expected, actual):
                return False
            if (column in needed and isinstance(expected, (int, float))
                    and not isinstance(expected, bool) and cell is not None
                    and (cell.number_format or "General") != row.number_formats.get(column, "General")):
                return False
            if cell is not None and cell.formula != row.formulas.get(column):
                return False
            if column in needed and row.formulas.get(column) and expected is None:
                return False
    for address, cell in cells.items():
        row, column_number = coordinate_to_tuple(address)
        if (top < row <= bottom and row not in table.excluded_rows
                and get_column_letter(column_number) in columns):
            if (cell.formula or cell.value not in (None, "")) and row not in source_rows:
                return False
    return True


def _same_value(expected, actual):
    if expected in (None, "") and actual in (None, ""):
        return True
    if isinstance(expected, bool) != isinstance(actual, bool):
        return False
    return expected == actual


def filtered_rows(table, filters):
    rows = list(table.rows)
    for condition in filters:
        if condition.operator not in {"equals", "not_equals", "contains", "is_blank", "not_blank"}:
            return None
        rows = [row for row in rows if _matches(row.values[condition.column_id], condition)]
    return rows


def _matches(value, condition):
    operator = condition.operator
    if operator == "is_blank":
        return value in (None, "")
    if operator == "not_blank":
        return value not in (None, "")
    if operator == "contains":
        return isinstance(value, str) and isinstance(condition.value, str) and condition.value in value
    equal = _same_value(value, condition.value)
    return equal if operator == "equals" else not equal
