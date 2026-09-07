from openpyxl.utils import get_column_letter

from app.agent.contracts import AgentToolContext
from app.agent.query.index import IndexedCell, IndexedRow, WorkbookDataIndex
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


def _evidence(sheet_name: str, reference: str) -> AnalysisEvidence:
    return AnalysisEvidence(
        kind=EvidenceKind.CELL,
        sheet_name=sheet_name,
        reference=reference,
        description="verified workbook fact",
    )
