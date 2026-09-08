from openpyxl.utils import get_column_letter

from app.agent.contracts import AgentToolContext
from app.agent.query.index import IndexedCell, IndexedRow, WorkbookDataIndex
from app.agent.query.query_rows import query_scope_truncated, with_relevant_priority_rows
from app.agent.tools import workbook_data
from app.services.provenance import AnalysisEvidence, EvidenceKind
from app.services.workbook_parsing.models import WorkbookSummary


def test_search_evidence_reserves_model_window_for_query_cells(monkeypatch) -> None:
    query_cells = tuple(
        IndexedCell(
            "Query",
            f"{get_column_letter(column)}1",
            "needle" if column == 1 else column,
            None,
        )
        for column in range(1, 51)
    )
    query_row = IndexedRow("Query", 1, query_cells)
    index = WorkbookDataIndex("test.xlsx", (query_row,), len(query_cells), False)
    verified_evidence = [_evidence("Verified", f"A{row}") for row in range(1, 141)]
    monkeypatch.setattr(
        workbook_data,
        "build_verified_question_context",
        lambda _workbook: {"overview": "", "insights": [], "calculations": []},
    )
    monkeypatch.setattr(
        workbook_data,
        "priority_evidence",
        lambda _rows, _verified: verified_evidence,
    )

    result = workbook_data.WorkbookDataSearchTool().execute(
        AgentToolContext(WorkbookSummary("test.xlsx", 0, []), index),
        {"query": "needle", "row_limit": 1},
    )

    model_evidence = result.evidence[:120]
    assert sum(item.sheet_name == "Query" for item in model_evidence) == 40
    assert len(result.evidence) == 190


def test_truncation_warning_is_limited_to_searched_sheets() -> None:
    index = WorkbookDataIndex(
        "test.xlsx", (), 50_000, True, frozenset({"Oversized Archive"})
    )

    assert not index.truncated_for({"Metrics"})
    assert index.truncated_for({"Oversized Archive"})
    assert index.truncated_for({"Metrics"}, whole_workbook=True)


def test_truncation_warning_remains_when_query_has_no_indexed_match() -> None:
    unrelated = IndexedRow(
        "Other", 1, (IndexedCell("Other", "A1", "unrelated", None),)
    )
    index = WorkbookDataIndex(
        "test.xlsx", (unrelated,), 50_000, True, frozenset({"Target"})
    )

    assert query_scope_truncated(index, [unrelated], "needle", False)


def test_verified_endpoint_row_is_added_to_selected_sheet() -> None:
    latest = _row(108, "2025-06-01", 1081)
    earliest = _row(115, "2023-09-01", 1277)
    verified = {
        "priority_references": ["Metrics!E108:W108", "Metrics!E115:W115"],
    }

    selected = with_relevant_priority_rows((latest, earliest), [latest], verified)

    assert [row.row_number for row in selected] == [108, 115]


def _evidence(sheet_name: str, reference: str) -> AnalysisEvidence:
    return AnalysisEvidence(
        kind=EvidenceKind.CELL,
        sheet_name=sheet_name,
        reference=reference,
        description="verified workbook fact",
    )


def _row(row_number: int, day: str, services: int) -> IndexedRow:
    return IndexedRow(
        "Metrics",
        row_number,
        (
            IndexedCell("Metrics", f"E{row_number}", day, None),
            IndexedCell("Metrics", f"W{row_number}", services, None),
        ),
    )
