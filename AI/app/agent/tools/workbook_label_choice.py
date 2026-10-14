"""무엇의 이름으로 나열할지 — 질문이 부른 열을 먼저 따른다.

"Handwash station이 x인 Outlet 알려줘"에 가게 이름이 아니라 그 옆 열의
면허번호가 나열된 적이 있다. 표시 열 왼쪽의 가장 가까운 글자 열을 고르면
질문이 이름을 직접 불러도 무시된다. 부른 열이 있으면 그 열로 나열한다.
"""
from app.agent.query.index import IndexedRow
from app.agent.tools.workbook_headers import HeaderContext
from app.agent.tools.workbook_label_columns import (
    column_of,
    labelled_column,
)
from app.agent.tools.workbook_row_conditions import matched_columns

MIN_NAMES = 4


def label_column(
    rows: list[IndexedRow],
    headers: HeaderContext,
    sheet_name: str,
    column: str,
    question: str,
):
    """(열, 머리글, 머리글 셀) 또는 이름 열을 찾지 못하면 None."""
    for found, candidate, header, reference in matched_columns(question, rows, headers):
        if found != sheet_name or candidate == column:
            continue
        if _names(rows, sheet_name, candidate, reference):
            return candidate, header, reference
    return labelled_column(rows, headers, sheet_name, column)


def _names(rows, sheet_name: str, column: str, reference: str) -> bool:
    """이름 열은 글자가 적혀 있고 값이 서로 달라야 한다."""
    values = [
        text
        for row in rows
        if row.sheet_name == sheet_name
        for cell in row.cells
        if column_of(cell.address) == column
        and isinstance(cell.value, str)
        and cell.reference != reference
        and (text := cell.value.strip())
    ]
    return len(values) >= MIN_NAMES and len(set(values)) > len(values) / 2
