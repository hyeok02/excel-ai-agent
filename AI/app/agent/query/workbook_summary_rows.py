import re
from collections import defaultdict

from app.agent.query.index import IndexedRow
from app.services.workbook_parsing.models import SheetSummary

SUMMARY_PHRASES = (
    "요약",
    "무슨 내용",
    "어떤 내용",
    "무엇을 담",
    "뭘 담",
    "파일 내용",
    "워크북 내용",
    "무엇을 비교",
    "핵심 내용",
    "핵심 수치",
    "가장 중요한",
    "summary",
    "overview",
)
WHOLE_FILE_SUBJECTS = (
    "파일", "워크북", "엑셀", "문서", "자료", "데이터",
    "workbook", "spreadsheet", "file",
)
WHOLE_FILE_ASKS = ("뭐", "무슨", "무엇", "어떤", "what", "about")
# 파일 자체를 묻는 질문에 흔히 붙는 말. 이것만 남으면 다른 대상이 없는 것이다.
WHOLE_FILE_FILLERS = (
    "관련", "얘기", "이야기", "내용", "담긴", "들어", "있어", "있나", "구성",
    "설명", "정리", "대해", "대한", "이거", "이건", "거야", "뭔가", "말하",
)
BUSINESS_TERMS = (
    "focus company",
    "company name",
    "total employees",
    "headcount",
    "department",
    "roles",
    "country / region",
    "transaction",
    "investment",
    "peer",
    "date",
)
FOCUS_TERMS = ("focus company", "focus co.", "analysis target", "분석 대상")
SUPPORT_SHEET_TERMS = (
    "chart_data",
    "intermediate",
    "raw_data",
    "cache",
    "lookup",
    "definition",
)


def is_workbook_summary_question(query: str) -> bool:
    normalized = " ".join(query.casefold().split())
    if any(phrase in normalized for phrase in SUMMARY_PHRASES):
        return True
    return _asks_about_the_whole_file(normalized)


def _asks_about_the_whole_file(normalized: str) -> bool:
    """'이 파일은 뭐에 관련된 얘기야?'처럼 파일 자체를 물을 때.

    정해 둔 표현 목록만 보면 같은 질문도 조금만 달리 쓰면 빗나간다. 파일을
    가리키는 말과 묻는 말이 함께 있고, 그 둘을 걷어낸 자리에 다른 대상이
    남지 않을 때만 워크북 전체 질문으로 본다. '이 파일 어떤 장비가 문제야?'는
    '장비'가 남으므로 전체 질문이 아니다.
    """
    if not any(term in normalized for term in WHOLE_FILE_SUBJECTS):
        return False
    if not any(ask in normalized for ask in WHOLE_FILE_ASKS):
        return False
    remaining = normalized
    for word in (*WHOLE_FILE_SUBJECTS, *WHOLE_FILE_ASKS, *WHOLE_FILE_FILLERS):
        remaining = remaining.replace(word, " ")
    return not any(
        len(token) >= 2 for token in re.findall(r"[0-9a-z]+|[가-힣]+", remaining)
    )


def select_workbook_summary_rows(
    rows: tuple[IndexedRow, ...], sheets: list[SheetSummary], limit: int
) -> list[IndexedRow]:
    by_sheet: dict[str, list[IndexedRow]] = defaultdict(list)
    for row in rows:
        by_sheet[row.sheet_name].append(row)
    ranked_sheets = sorted(
        (sheet for sheet in sheets if not _is_support_sheet(sheet.name)),
        key=_sheet_score,
        reverse=True,
    )[:5]
    selected = []
    seen: set[tuple[str, int]] = set()
    for sheet in ranked_sheets:
        candidates = by_sheet.get(sheet.name, [])
        anchors = sorted(candidates, key=_row_score, reverse=True)[:2]
        for anchor in anchors:
            for row in _with_following(candidates, anchor):
                key = (row.sheet_name, row.row_number)
                if key not in seen:
                    selected.append(row)
                    seen.add(key)
                if len(selected) >= limit:
                    return selected
    return selected


def _sheet_score(sheet: SheetSummary) -> int:
    classification = sheet.sheet_classification
    if classification is None:
        return 0
    role_scores = {"output": 50, "documentation": 20, "calculation": 10, "input": 5}
    return classification.importance_score + role_scores.get(classification.role, 0)


def _row_score(row: IndexedRow) -> tuple[int, int, int, int]:
    focus_hits = sum(term in row.search_text for term in FOCUS_TERMS)
    hits = sum(term in row.search_text for term in BUSINESS_TERMS)
    text_count = sum(isinstance(cell.value, str) for cell in row.cells)
    return focus_hits, hits, text_count, -row.row_number


def _with_following(rows: list[IndexedRow], anchor: IndexedRow) -> list[IndexedRow]:
    offsets = (0, 1) if any(
        term in anchor.search_text for term in FOCUS_TERMS
    ) else (0, 1, 8)
    row_numbers = {anchor.row_number + offset for offset in offsets}
    return [row for row in rows if row.row_number in row_numbers]


def _is_support_sheet(name: str) -> bool:
    normalized = name.casefold()
    return any(term in normalized for term in SUPPORT_SHEET_TERMS)
