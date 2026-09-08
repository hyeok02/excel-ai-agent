from app.agent.query.index import IndexedRow, WorkbookDataIndex
from app.agent.query.references import normalize_reference
from app.agent.query.search_terms import relevance, search_terms
from app.agent.query.verified_evidence import priority_evidence


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
