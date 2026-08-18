from app.services.insight_generator import (
    MAX_FORMULAS_PER_SHEET,
    build_workbook_context,
)
from app.services.formula_analyzer import FormulaAnalysis
from app.services.region_detector import CellRegion
from app.services.workbook_parser import SheetSummary, WorkbookSummary


def test_limits_workbook_context_for_llm_prompt() -> None:
    formulas = [
        FormulaAnalysis(
            cell=f"A{index}",
            formula=f"=B{index}+C{index}",
            references=[f"B{index}", f"C{index}"],
        )
        for index in range(MAX_FORMULAS_PER_SHEET + 3)
    ]
    summary = WorkbookSummary(
        filename="large.xlsx",
        sheet_count=1,
        sheets=[
            SheetSummary(
                name="계산",
                rows=100,
                columns=3,
                formula_count=len(formulas),
                table_count=0,
                chart_count=0,
                formulas=formulas,
                region_count=1,
                regions=[CellRegion(start_cell="A1", end_cell="C100", cell_count=300)],
            )
        ],
    )

    context = build_workbook_context(summary)
    sheet = context["sheets"][0]

    assert len(sheet["formula_samples"]) == MAX_FORMULAS_PER_SHEET
    assert sheet["omitted_formula_count"] == 3
    assert sheet["region_samples"] == [
        {"start_cell": "A1", "end_cell": "C100", "cell_count": 300}
    ]
