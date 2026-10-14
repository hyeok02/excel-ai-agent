from dataclasses import dataclass

from app.agent.query.index import IndexedRow, WorkbookDataIndex
from app.agent.query.references import normalize_reference
from app.agent.query.row_search import search_matched
from app.agent.query.search_terms import relevance, search_terms
from app.agent.query.verified_evidence import priority_evidence
from app.agent.query.workbook_summary_rows import select_workbook_summary_rows
from app.services.workbook_parsing.models import SheetSummary


@dataclass(frozen=True)
class QuestionRows:
    rows: list[IndexedRow]
    whole_workbook: bool


def selected_question_rows(
    index: WorkbookDataIndex,
    sheets: list[SheetSummary],
    query: str,
    limit: int,
    summary_question: bool,
) -> QuestionRows:
    """질문에 쓸 행.

    검색이 질문의 낱말을 하나도 못 걸었으면 아무 행이나 넘기지 않는다. 그
    경우 묻는 대상이 워크북 전체이거나 표현이 표의 말과 달랐다는 뜻이므로,
    워크북을 대표하는 행으로 바꾼다. 의도 판별이 틀렸을 때도 이 안전망이
    모델에게 엉뚱한 행이 가는 것을 막는다.
    """
    if summary_question:
        return QuestionRows(select_workbook_summary_rows(index.rows, sheets, limit), True)
    found = search_matched(index.rows, query, limit)
    if found.matched:
        return QuestionRows(found.rows, False)
    return QuestionRows(select_workbook_summary_rows(index.rows, sheets, limit), True)


def with_relevant_priority_rows(
    rows: tuple[IndexedRow, ...],
    selected: list[IndexedRow],
    verified: dict[str, object],
) -> list[IndexedRow]:
    """Bring verified endpoint rows into the query's already selected sheets."""
    selected_sheets = {row.sheet_name for row in selected}
    references = {
        normalized
        for item in priority_evidence(rows, verified)
        if (normalized := normalize_reference(f"{item.sheet_name}!{item.reference}"))
    }
    additions = [
        row
        for row in rows
        if row.sheet_name in selected_sheets
        and any(normalize_reference(cell.reference) in references for cell in row.cells)
    ]
    return list(
        {
            (row.sheet_name, row.row_number): row
            for row in [*selected, *additions]
        }.values()
    )


def query_scope_truncated(
    index: WorkbookDataIndex,
    rows: list[IndexedRow],
    query: str,
    whole_workbook: bool,
) -> bool:
    searched_sheets = {row.sheet_name for row in rows}
    if index.truncated_for(searched_sheets, whole_workbook):
        return True
    if not index.truncated:
        return False
    terms = search_terms(query)
    return not terms or not any(relevance(row, terms) for row in rows)
