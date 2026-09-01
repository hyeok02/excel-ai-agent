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
    "summary",
    "overview",
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
    return any(phrase in normalized for phrase in SUMMARY_PHRASES)


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
