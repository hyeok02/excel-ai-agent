"""질문이 가리키는 열과 조건을 읽는다."""
from app.agent.query.index import IndexedRow
from app.agent.tools.workbook_headers import HeaderContext, header_for

NEGATIVE_MARKS = {"x"}
POSITIVE_MARKS = {"o", "v"}
# 조사가 붙어도 걸리도록 어간만 둔다.
NEGATIVE_STEMS = ("안", "못", "없", "불", "미", "아닌", "아직")
POSITIVE_STEMS = ("된", "됨", "완료", "있", "정상", "끝난")
MIN_TERM = 2


def requested_condition(
    question: str, rows: list[IndexedRow], headers: HeaderContext
):
    """(시트, 열, 머리글, 머리글 셀, 극성) 또는 질문이 분명하지 않으면 None."""
    best = _matched_column(question, rows, headers)
    if best is None:
        return None
    sheet_name, column, header, reference = best
    polarity = _polarity(question, header)
    if polarity is None:
        return None
    return sheet_name, column, header, reference, polarity


def _matched_column(question: str, rows: list[IndexedRow], headers: HeaderContext):
    """질문에 이름이 나온 열. 머리글과 가장 길게 겹치는 쪽을 고른다."""
    normalized = question.casefold()
    best = None
    for row in rows:
        for cell in row.cells:
            header = header_for(headers, row.sheet_name, row.row_number, cell.address)
            if not header:
                continue
            overlap = _overlap(normalized, header.casefold())
            if overlap >= MIN_TERM and (best is None or overlap > best[0]):
                best = (overlap, row.sheet_name, _column(cell.address), header)
    if best is None:
        return None
    _, sheet_name, column, header = best
    reference = _header_reference(rows, headers, sheet_name, column, header)
    return (sheet_name, column, header, reference) if reference else None


def _overlap(question: str, header: str) -> int:
    """머리글의 낱말 중 질문에 그대로 나오는 글자 수."""
    return sum(
        len(word) for word in header.replace("(", " ").replace(",", " ").split()
        if len(word) >= MIN_TERM and word in question
    )


def _polarity(question: str, header: str) -> str | None:
    """
    머리글에 쓰인 말을 걷어낸 나머지에서 긍정·부정을 읽는다.

    '네트워크 안정'이라는 머리글을 그대로 두고 보면 '안정된'의 '안'이 부정으로
    읽힌다. 머리글의 낱말을 지우고 남은 자리만 봐야 '불안정한'과 '안정된'이
    갈린다.
    """
    residue = question.casefold()
    for word in header.casefold().replace("(", " ").replace(",", " ").split():
        if len(word) >= MIN_TERM:
            residue = residue.replace(word, " ")
    if any(stem in residue for stem in NEGATIVE_STEMS):
        return "negative"
    if any(stem in residue for stem in POSITIVE_STEMS):
        return "positive"
    return None


def labelled_column(
    rows: list[IndexedRow], headers: HeaderContext, sheet_name: str, column: str
):
    """무엇을 나열할지. 표시 열 왼쪽에서 값이 서로 다른 가장 가까운 글자 열."""
    candidates: dict[str, list] = {}
    for row in rows:
        if row.sheet_name != sheet_name:
            continue
        for cell in row.cells:
            found = _column(cell.address)
            if _index(found) < _index(column) and isinstance(cell.value, str):
                candidates.setdefault(found, []).append(cell)
    for found in sorted(candidates, key=_index, reverse=True):
        values = [str(cell.value).strip() for cell in candidates[found]]
        values = [value for value in values if value]
        if len(values) < 4 or len(set(values)) <= len(values) / 2:
            continue
        header = next(
            (
                header
                for row in rows
                for cell in row.cells
                if _column(cell.address) == found
                and (header := header_for(headers, sheet_name, row.row_number, cell.address))
            ),
            None,
        )
        reference = _header_reference(rows, headers, sheet_name, found, header)
        if header and reference:
            return found, header, reference
    return None


def _header_reference(rows, headers, sheet_name, column, header):
    for row in rows:
        if row.sheet_name != sheet_name:
            continue
        for cell in row.cells:
            if _column(cell.address) == column and str(cell.value or "").strip() == header:
                return cell.reference
    return None


def _column(address: str) -> str:
    return "".join(character for character in address if character.isalpha()).upper()


def _index(column: str) -> int:
    value = 0
    for character in column:
        value = value * 26 + (ord(character) - 64)
    return value
