"""'o가 제일 많은 항목은?' — 표시가 가장 많은 열을 코드가 직접 센다.

모델에게 맡기면 열을 세다 틀리고, 틀린 수는 검증에 걸려 답변이 사라진다.
더 나쁘게는, 셀 수 없으면 파일 전체 요약이 대신 나가 특정 질문에 엉뚱한
답이 '근거 확인' 딱지를 달고 나갔다.
"""
from app.agent.query.index import IndexedRow
from app.agent.tools.workbook_headers import HeaderContext, header_for
from app.agent.tools.workbook_label_columns import column_of, is_hangul
from app.services.insights.facts.flag_columns import mark_of

SUPERLATIVE_WORDS = ("제일", "가장", "최다", "최대", "most", "highest")
MAX_PARTICLE = 2
MIN_MARKED = 3


def build_mark_peak(
    rows: list[IndexedRow], headers: HeaderContext, question: str
) -> dict[str, object] | None:
    normalized = question.casefold()
    if not any(word in normalized for word in SUPERLATIVE_WORDS):
        return None
    mark = _asked_mark(normalized)
    if mark is None:
        return None
    best = None
    for sheet_name in {row.sheet_name for row in rows}:
        for found in _counted(rows, headers, sheet_name, mark):
            if best is None or found["count"] > best["count"]:
                best = found
    return best


def _counted(rows, headers, sheet_name, mark):
    columns: dict[str, list] = {}
    for row in rows:
        if row.sheet_name != sheet_name:
            continue
        for cell in row.cells:
            if mark_of(cell.value) is not None and len(str(cell.value).strip()) <= 2:
                columns.setdefault(column_of(cell.address), []).append((row, cell))
    for column, found in columns.items():
        if len(found) < MIN_MARKED:
            continue
        hit = [(row, cell) for row, cell in found if mark_of(cell.value) == mark]
        if not hit:
            continue
        header = next(
            (
                name
                for row, cell in found
                if (name := header_for(headers, sheet_name, row.row_number, cell.address))
            ),
            None,
        )
        reference = _header_reference(rows, sheet_name, column, header)
        if header and reference:
            yield {
                "sheet_name": sheet_name,
                "header": header,
                "header_reference": reference,
                "mark": mark,
                "count": len(hit),
                "first_reference": hit[0][1].reference,
                "last_reference": hit[-1][1].reference,
            }


def _header_reference(rows, sheet_name, column, header):
    for row in rows:
        if row.sheet_name != sheet_name:
            continue
        for cell in row.cells:
            if column_of(cell.address) == column and str(cell.value or "").strip() == header:
                return cell.reference
    return None


def _asked_mark(normalized: str) -> str | None:
    """'o가', 'x인'처럼 표시 한 글자에 조사만 붙은 낱말에서 표시를 읽는다."""
    for word in normalized.split():
        token = word.strip(".,:;?!()'\"‘’“”")
        if not token or token[0].isdigit():
            continue
        suffix = token[1:]
        if len(suffix) > MAX_PARTICLE or not all(is_hangul(ch) for ch in suffix):
            continue
        if (mark := mark_of(token)) is not None:
            return mark
    return None
