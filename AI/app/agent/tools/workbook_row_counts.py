"""몇 건인지, 그리고 한 항목의 값이 얼마인지를 코드가 직접 센다.

"장비가 총 몇 대야?"나 "#1 호기 IP가 뭐야?"는 표를 한 번 훑으면 끝나는
질문이다. 모델에게 맡기면 셀을 빠뜨리거나 세다 틀리고, 틀린 수는 검증에
걸려 답변이 통째로 사라진다.
"""
from app.agent.query.index import IndexedRow
from app.agent.query.search_terms import search_terms
from app.agent.tools.workbook_headers import HeaderContext, header_for
from app.agent.tools.workbook_label_choice import label_column
from app.agent.tools.workbook_label_columns import column_of
from app.agent.tools.workbook_metric_matching import contains_term

COUNT_WORDS = ("몇", "개수", "건수", "how many", "count")
SUBSET_WORDS = (
    "점검된", "완료된", "점검 완료", "기재된", "표시된", "비어", "미점검",
    "completed", "checked", "marked", "blank", "missing",
)
MIN_ROWS = 2


def build_row_count(
    rows: list[IndexedRow], headers: HeaderContext, question: str
) -> dict[str, object] | None:
    """질문이 개수를 물을 때, 이름 열의 기재 건수를 센다."""
    normalized = question.casefold()
    if (
        not any(contains_term(normalized, word) for word in COUNT_WORDS)
        or any(word in normalized for word in SUBSET_WORDS)
    ):
        return None
    best = None
    for sheet_name in {row.sheet_name for row in rows}:
        found = _counted(rows, headers, sheet_name, question)
        if found and (best is None or found["count"] > best["count"]):
            best = found
    return best


def _counted(rows, headers, sheet_name, question):
    marked = _marked_column(rows, headers, sheet_name)
    if marked is None:
        return None
    label = label_column(rows, headers, sheet_name, marked, question)
    if label is None:
        return None
    column, header, reference = label
    values = [
        cell
        for row in rows
        if row.sheet_name == sheet_name
        for cell in row.cells
        if column_of(cell.address) == column
        and isinstance(cell.value, str)
        and cell.value.strip()
        and cell.reference != reference
    ]
    if len(values) < MIN_ROWS or not _names_the_column(question, header):
        return None
    return {
        "sheet_name": sheet_name,
        "header": header,
        "header_reference": reference,
        "count": len(values),
        "first_reference": values[0].reference,
        "last_reference": values[-1].reference,
    }


def _names_the_column(question: str, header: str) -> bool:
    """질문이 그 열을 가리켜야 센다. '몇'만 보고 아무 열이나 세지 않는다."""
    terms = search_terms(question)
    normalized = header.casefold()
    return any(len(term) >= 2 and term in normalized for term in terms)


def _marked_column(rows, headers, sheet_name) -> str | None:
    """표시가 반복되는 열. 그 왼쪽에서 이름 열을 찾기 위한 기준점이다."""
    counts: dict[str, list[str]] = {}
    for row in rows:
        if row.sheet_name != sheet_name:
            continue
        for cell in row.cells:
            if isinstance(cell.value, str) and len(cell.value.strip()) <= 2:
                counts.setdefault(column_of(cell.address), []).append(cell.value.strip())
    repeated = [
        column for column, values in counts.items()
        if len(values) >= MIN_ROWS and len(set(values)) < len(values)
    ]
    return min(repeated, key=_index) if repeated else None


def _index(column: str) -> int:
    value = 0
    for character in column:
        value = value * 26 + (ord(character) - 64)
    return value
