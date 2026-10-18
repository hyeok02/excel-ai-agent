"""Re-read source headers and rows without treating absent samples as blanks."""
from openpyxl.utils import coordinate_to_tuple, get_column_letter, range_boundaries

from app.agent.query.ambiguity_labels import source_mentioned
from app.agent.query.ambiguity_qualifiers import explicit_column_ids
from app.agent.query.tabular_catalog_models import QueryRow
from app.agent.query.tabular_filters import matches
from app.agent.query.tabular_request_scope import header_request_text


def source_scope(provider, index, table, needed, tables, question):
    if (not index.source_digest or provider.source_digest != index.source_digest
            or table.sheet_name not in provider.authorized_sheets
            or table.source_kind not in {"native", "schema", "region", "report"}
            or not table.complete and table.source_kind == "report"):
        return None
    sheet = provider.sheet(table.sheet_name)
    if sheet is None:
        return None
    left, top, right, bottom = range_boundaries(table.reference)
    if top in sheet.hidden_rows or right > sheet.columns or bottom > sheet.rows:
        return None
    hidden = needed & (sheet.hidden_columns | table.hidden_columns)
    explicit = explicit_column_ids(question)
    field_text = header_request_text(question, {candidate.sheet_name for candidate in tables})
    if any(column.id in hidden and column.id not in explicit and not source_mentioned(column.header, field_text)
           for column in table.columns):
        return None
    if any(coordinate_to_tuple(column.header_reference.rpartition("!")[2])[0] != top for column in table.columns):
        return None
    for span in sheet.merged_ranges:
        a, b, c, d = range_boundaries(span)
        if a <= right and left <= c and b <= bottom and top < d and (a != c or b != d):
            return None
    for other in tables:
        if other.id == table.id or other.sheet_name != table.sheet_name:
            continue
        a, b, c, d = range_boundaries(other.reference)
        if a <= right and left <= c and b <= bottom and top <= d:
            return None
    return sheet


def header_matches(row, table):
    cells = {cell.address: cell for cell in row.cells}
    for column in table.columns:
        source = cells.get(column.header_reference.rpartition("!")[2])
        if source is None or not isinstance(source.value, str) or source.value.strip() != column.header:
            return False
    return True


def source_row(row, table):
    by_column = {get_column_letter(coordinate_to_tuple(cell.address)[1]): cell for cell in row.cells}
    values = {column.id: by_column[column.id].value if column.id in by_column else None for column in table.columns}
    formulas = {column: cell.formula for column, cell in by_column.items() if column in values and cell.formula}
    formats = {column: cell.number_format or "General" for column, cell in by_column.items()
               if column in values and cell.value not in (None, "")}
    return QueryRow(row.row_number, values, formulas, formats)


def row_eligible(row, plan, table):
    headers = {column.id: column.header for column in table.columns}
    for condition in plan.filters:
        result = matches(row.values[condition.column_id], condition,
                         row.number_formats.get(condition.column_id, "General"), headers[condition.column_id])
        if result is None:
            return None
        if not result:
            return False
    return True


