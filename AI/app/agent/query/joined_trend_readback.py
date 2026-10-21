"""Recover complete join sides and retain their real source-addressed cells."""
from dataclasses import replace
from openpyxl.utils import range_boundaries

from app.agent.query.tabular_catalog_models import QueryRow
from app.agent.query.trend_source_context import verified_context
from app.agent.query.trend_source_readback import table_rows, column_cells
from app.agent.query.workbook_source import source_for


def read_join_side(table, tables, index, question):
    rows, error = table_rows(table, tables, index, question)
    if error:
        raise ValueError("연결할 원본 표 전체를 대조하지 못했습니다. 일부 표본 행만 연결하지 않았습니다.")
    _, top, _, bottom = range_boundaries(table.reference)
    hidden = set(table.excluded_rows)
    provider = source_for(index)
    if provider:
        if table.sheet_name not in provider.authorized_sheets:
            raise ValueError("연결할 원본 시트의 접근 범위를 확인하지 못했습니다.")
        hidden.update(number for number in provider.sheet(table.sheet_name).hidden_rows if top < number <= bottom)
    if hidden or table.hidden_columns:
        raise ValueError("숨겨진 행·열이 있는 표의 전체 연결 범위를 확정하지 않았습니다.")
    cells = {cell.reference: cell for row in rows for cell in row.cells}
    headers = {column.id: cells.get(column.header_reference) for column in table.columns}
    context = verified_context(table.context, index)
    if any(cell is None for cell in headers.values()) or context is None:
        raise ValueError("연결할 표의 머리글·설명 셀을 원본과 대조하지 못했습니다.")
    records = {row.row_number: column_cells(row) for row in rows if row.row_number > top and row.cells}
    records = {number: record for number, record in records.items()
               if any(cell.value not in (None, "") or cell.formula for cell in record.values())}
    complete = tuple(QueryRow(number, {column.id: record[column.id].value if column.id in record else None
                                     for column in table.columns},
                             {key: cell.formula for key, cell in record.items() if cell.formula},
                             {key: cell.number_format for key, cell in record.items()})
                     for number, record in records.items())
    return replace(table, rows=complete, complete=True), records, headers, tuple(context)
