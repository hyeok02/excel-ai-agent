from app.services.insight_generator import (
    MAX_FORMULAS_PER_SHEET,
    build_workbook_context,
)
from app.services.formula_analyzer import FormulaAnalysis
from app.services.region_detector import CellRegion
from app.services.workbook_details import (
    CellSnapshot,
    HeaderPathSummary,
    RegionSummary,
)
from app.services.workbook_parser import SheetSummary, WorkbookSummary


def test_deduplicates_formula_patterns_for_llm_prompt() -> None:
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

    assert len(sheet["formula_samples"]) == 1
    assert sheet["formula_samples"][0]["cell"] == "A0"
    assert sheet["omitted_formula_count"] == MAX_FORMULAS_PER_SHEET + 2
    assert sheet["region_samples"] == [
        {
            "start_cell": "A1",
            "end_cell": "C100",
            "cell_count": 300,
            "title": None,
            "row_count": None,
            "column_count": None,
            "merged_range_count": 0,
            "header_paths": [],
        }
    ]


def test_excludes_cell_previews_from_llm_prompt_context() -> None:
    summary = WorkbookSummary(
        filename="preview.xlsx",
        sheet_count=1,
        sheets=[
            SheetSummary(
                name="데이터",
                rows=20,
                columns=5,
                formula_count=0,
                table_count=0,
                chart_count=0,
                formulas=[],
                region_count=1,
                regions=[
                    RegionSummary(
                        start_cell="A1",
                        end_cell="E20",
                        cell_count=100,
                        title="매출 현황",
                        row_count=20,
                        column_count=5,
                        merged_ranges=["A1:E1"],
                        header_paths=[
                            HeaderPathSummary(column="A", labels=["부서"])
                        ],
                        preview_rows=[
                            [
                                CellSnapshot(
                                    address="A1",
                                    value="LLM에 전송하면 안 되는 원본 미리보기",
                                    formula=None,
                                )
                            ]
                        ],
                        is_truncated=True,
                    )
                ],
            )
        ],
    )

    context = build_workbook_context(summary)
    region = context["sheets"][0]["region_samples"][0]

    assert region["title"] == "매출 현황"
    assert region["merged_range_count"] == 1
    assert region["header_paths"] == [{"column": "A", "labels": ["부서"]}]
    assert "preview_rows" not in region
