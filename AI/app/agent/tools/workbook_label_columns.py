"""무엇을 나열할지 — 표에서 이름 열을 찾는다."""
from app.agent.query.index import IndexedRow
from app.agent.tools.workbook_headers import HeaderContext, header_for

MIN_NAMES = 4


def labelled_column(
    rows: list[IndexedRow], headers: HeaderContext, sheet_name: str, column: str
):
    """무엇을 나열할지. 표시 열 왼쪽에서 값이 서로 다른 가장 가까운 글자 열."""
    candidates: dict[str, list] = {}
    for row in rows:
        if row.sheet_name != sheet_name:
            continue
        for cell in row.cells:
            found = column_of(cell.address)
            if _index(found) < _index(column) and isinstance(cell.value, str):
                candidates.setdefault(found, []).append(cell)
    for found in sorted(candidates, key=_index, reverse=True):
        values = [str(cell.value).strip() for cell in candidates[found]]
        values = [value for value in values if value]
        if len(values) < MIN_NAMES or len(set(values)) <= len(values) / 2:
            continue
        header = next(
            (
                header
                for row in rows
                for cell in row.cells
                if column_of(cell.address) == found
                and (header := header_for(headers, sheet_name, row.row_number, cell.address))
            ),
            None,
        )
        reference = header_reference(rows, headers, sheet_name, found, header)
        if header and reference:
            return found, header, reference
    return None


def header_reference(rows, headers, sheet_name, column, header):
    for row in rows:
        if row.sheet_name != sheet_name:
            continue
        for cell in row.cells:
            if column_of(cell.address) == column and str(cell.value or "").strip() == header:
                return cell.reference
    return None


def column_of(address: str) -> str:
    return "".join(character for character in address if character.isalpha()).upper()


def _index(column: str) -> int:
    value = 0
    for character in column:
        value = value * 26 + (ord(character) - 64)
    return value


def is_hangul(character: str) -> bool:
    return "가" <= character <= "힣"
