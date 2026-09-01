from types import SimpleNamespace

from openpyxl.worksheet.formula import ArrayFormula

from app.agent.query.cell_values import formula_text, safe_indexed_value
from app.agent.query.index import IndexedCell, IndexedRow
from app.agent.query.router import build_question_plan
from app.agent.query.service import _available_evidence
from app.agent.query.workbook_summary_rows import select_workbook_summary_rows
from app.services.provenance import AnalysisEvidence, EvidenceKind


def test_summary_question_also_inspects_semantic_structure() -> None:
    plan = build_question_plan("이 엑셀 파일이 무슨 내용을 담고 있는지 요약해줘")

    assert [step.tool_name for step in plan.steps] == [
        "search_workbook_data",
        "inspect_semantic_structure",
    ]


def test_summary_rows_prioritize_business_outputs_over_support_data() -> None:
    rows = (
        _row("Chart_Data", 7, "Afghanistan", 100),
        _row("Intermediate", 1, "raw calculation", 100),
        _row("Detailed_Headcount_Analytics", 6, "Focus Company Riot Games", 4),
        _row(
            "Detailed_Headcount_Analytics",
            107,
            "Date Total Employees Department Roles Country / Region",
            12,
        ),
        _row("Detailed_Headcount_Analytics", 108, "2025-06-01 5417", 12),
        _row("Transaction_KeyDev_Details", 5, "Transaction Date Investment", 8),
    )
    sheets = [
        _sheet("Chart_Data", "input", 90),
        _sheet("Intermediate", "calculation", 95),
        _sheet("Detailed_Headcount_Analytics", "output", 91),
        _sheet("Transaction_KeyDev_Details", "output", 60),
    ]

    selected = select_workbook_summary_rows(rows, sheets, 12)
    names = {row.sheet_name for row in selected}

    assert "Detailed_Headcount_Analytics" in names
    assert "Transaction_KeyDev_Details" in names
    assert "Chart_Data" not in names
    assert "Intermediate" not in names
    assert any(row.row_number == 6 for row in selected)


def test_array_formula_is_serialized_without_python_object_details() -> None:
    formula = formula_text(ArrayFormula("B7:B8", "=SP_HEADCOUNT_COUNTRY()"))
    unsupported_value, value_type = safe_indexed_value(object(), None)

    assert formula == "=SP_HEADCOUNT_COUNTRY()"
    assert "openpyxl" not in formula
    assert unsupported_value is None
    assert value_type == "unsupported"


def test_cell_value_evidence_is_not_overwritten_by_structure_evidence() -> None:
    rich = _evidence("Riot Games, Inc.")
    empty = _evidence(None)
    execution = SimpleNamespace(
        steps=[
            SimpleNamespace(result=SimpleNamespace(evidence=[rich])),
            SimpleNamespace(result=SimpleNamespace(evidence=[empty])),
        ]
    )

    selected = _available_evidence(execution)

    assert selected["analysis!d6"].value == "Riot Games, Inc."


def _row(sheet: str, number: int, text: str, width: int) -> IndexedRow:
    cells = [IndexedCell(sheet, f"A{number}", text, None)]
    cells.extend(
        IndexedCell(sheet, f"C{index}{number}", index, None)
        for index in range(1, width)
    )
    return IndexedRow(sheet, number, tuple(cells))


def _sheet(name: str, role: str, score: int):
    classification = SimpleNamespace(
        role=role,
        importance_score=score,
    )
    return SimpleNamespace(name=name, sheet_classification=classification)


def _evidence(value: str | None) -> AnalysisEvidence:
    return AnalysisEvidence(
        kind=EvidenceKind.CELL,
        sheet_name="Analysis",
        reference="D6",
        description="Focus Company",
        value=value,
    )
