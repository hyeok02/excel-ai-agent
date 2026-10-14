"""한 항목의 한 값을 짚어 준다.

"#1 호기 IP가 뭐야?"는 표에서 행 하나와 열 하나가 만나는 칸을 읽으면 끝난다.
모델에게 맡기면 이웃 행의 값을 집어 오기 쉽고, 그러면 검증에서 답변이 통째로
버려진다.
"""
from collections import Counter

from app.agent.query.index import IndexedRow
from app.agent.tools.workbook_headers import HeaderContext
from app.agent.tools.workbook_label_columns import column_of, labelled_column
from app.agent.tools.workbook_row_conditions import matched_columns

MIN_TOKEN = 2
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
    label = labelled_column(rows, headers, sheet_name, column) or _naming_column(
        rows, headers, sheet_name, column
    )
    if label is None:
        return None
    label_column, label_header, label_reference = label
    named = _named_row(rows, sheet_name, label_column, question, label_reference)
    if named is None:
        return None
    name, name_cell = named
    value = next(
        (
            cell
            for cell in name_cell[1].cells
            if column_of(cell.address) == column
            and str(cell.value or "").strip()
        ),
        None,
    )
    if value is None:
        return None
    return {
        "sheet_name": sheet_name,
        "header": header,
        "header_reference": header_reference,
        "label_header": label_header,
        "label": name,
        "label_reference": name_cell[0].reference,
        "value": value.value,
        "value_reference": value.reference,
    }


def _naming_column(rows, headers, sheet_name, target):
    """
    이름 열이 값 열의 오른쪽에 있을 수도 있다.

    표시 열을 찾을 때는 왼쪽만 보면 되지만, 'IP가 뭐야?'처럼 값 열을 물으면
    그 열이 표의 맨 왼쪽일 수 있다. 그때는 양쪽에서 이름 열을 찾는다.
    """
    best = None
    for column in _text_columns(rows, sheet_name):
        if column == target:
            continue
        label = labelled_column(rows, headers, sheet_name, _next_column(column))
        if label and label[0] == column and (best is None or _index(column) < _index(best[0])):
            best = label
    return best


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


def _named_row(rows, sheet_name, label_column, question, header_reference):
    """
    질문이 한 행만 가리킬 때 그 행. 둘 이상 걸리면 짚지 않는다.

    'CVD #1'과 'CVD #11'은 'cvd'를 함께 쓴다. 모든 이름이 공유하는 낱말로는
    행을 고를 수 없으므로, 한 행에만 있는 낱말로 가리켰을 때만 인정한다.
    """
    asked = _tokens(question)
    candidates = []
    for row in rows:
        if row.sheet_name != sheet_name:
            continue
        for cell in row.cells:
            if column_of(cell.address) != label_column:
                continue
            text = str(cell.value or "").strip()
            if text and cell.reference != header_reference:
                candidates.append((text, _tokens(text), (cell, row)))
    shared = Counter(token for _, tokens, _ in candidates for token in tokens)
    distinctive = {token for token in asked if shared.get(token) == 1}
    if not distinctive:
        return None
    found = [
        (text, place) for text, tokens, place in candidates if tokens & distinctive
    ]
    return found[0] if len(found) == 1 else None


def _tokens(text: str) -> set[str]:
    """'CVD #1' 과 'CVD #11' 이 섞이지 않게 낱말 단위로 맞춘다."""
    return {
        token.strip(".,:;?!()").casefold()
        for token in str(text).split()
        if len(token.strip(".,:;?!()")) >= MIN_TOKEN
    }
