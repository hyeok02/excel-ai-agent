"""한 항목의 한 값을 짚어 준다.

"#1 호기 IP가 뭐야?"는 표에서 행 하나와 열 하나가 만나는 칸을 읽으면 끝난다.
모델에게 맡기면 이웃 행의 값을 집어 오기 쉽고, 그러면 검증에서 답변이 통째로
버려진다.
"""
from app.agent.query.index import IndexedRow
from app.agent.tools.workbook_headers import HeaderContext
from app.agent.tools.workbook_label_columns import column_of, labelled_column
from app.agent.tools.workbook_lookup_guards import lookup_header_matches, scalar_lookup_question
from app.agent.tools.workbook_row_conditions import matched_columns
from app.agent.tools.workbook_row_names import named_row

MAX_CANDIDATES = 6


def build_cell_lookup(
    rows: list[IndexedRow], headers: HeaderContext, question: str
) -> dict[str, object] | None:
    for candidate in matched_columns(question, rows, headers)[:MAX_CANDIDATES]:
        found = _looked_up(rows, headers, question, candidate)
        if found:
            return found
    return None


def _looked_up(rows, headers, question, candidate):
    sheet_name, column, header, header_reference = candidate
    if not lookup_header_matches(question, header):
        return None
    matches = []
    for label_column, label_header, label_reference in _naming_columns(
        rows, headers, sheet_name, column
    ):
        named = named_row(rows, sheet_name, label_column, question, label_reference)
        if named is not None:
            matches.append((label_header, named))
    row_numbers = {named[1][1].row_number for _, named in matches}
    if len(row_numbers) != 1:
        return None
    label_header, (name, name_cell) = matches[0]
    if not scalar_lookup_question(question, header, name):
        return None
    header_row = int("".join(char for char in header_reference.rsplit("!", 1)[-1] if char.isdigit()))
    if name_cell[1].row_number <= header_row:
        return None
    value = next(
        (
            cell for cell in name_cell[1].cells
            if column_of(cell.address) == column
            and cell.value is not None and str(cell.value).strip()
        ),
        None,
    )
    if value is None:
        return None
    return {
        "sheet_name": sheet_name, "header": header,
        "header_reference": header_reference, "label_header": label_header,
        "label": name, "label_reference": name_cell[0].reference,
        "value": value.value, "value_reference": value.reference,
    }


def _naming_columns(rows, headers, sheet_name, target):
    """
    이름 열이 값 열의 오른쪽에 있을 수도 있다.

    표시 열을 찾을 때는 왼쪽만 보면 되지만, 'IP가 뭐야?'처럼 값 열을 물으면
    그 열이 표의 맨 왼쪽일 수 있다. 그때는 양쪽에서 이름 열을 찾는다.
    """
    found = []
    primary = labelled_column(
        rows, headers, sheet_name, target, minimum_names=1
    )
    if primary:
        found.append(primary)
    for column in _text_columns(rows, sheet_name):
        if column == target:
            continue
        label = labelled_column(
            rows, headers, sheet_name, _next_column(column), minimum_names=1
        )
        if label and label[0] == column and label not in found:
            found.append(label)
    return found


def _text_columns(rows, sheet_name) -> list[str]:
    columns = {
        column_of(cell.address)
        for row in rows
        if row.sheet_name == sheet_name
        for cell in row.cells
        if isinstance(cell.value, str) and cell.value.strip()
    }
    return sorted(columns, key=_index)


def _next_column(column: str) -> str:
    value = _index(column) + 1
    letters = ""
    while value:
        value, remainder = divmod(value - 1, 26)
        letters = chr(65 + remainder) + letters
    return letters


def _index(column: str) -> int:
    value = 0
    for character in column:
        value = value * 26 + (ord(character) - 64)
    return value
