from app.services.insight_generator import (
    MAX_FORMULAS_PER_SHEET,
    build_user_prompt,
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
            "analysis_inclusion": None,
            "merged_range_count": 0,
            "header_paths": [],
        }
    ]


def test_selects_business_values_without_sending_full_previews() -> None:
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
                                    value="Riot Games, Inc.",
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
    assert region["analysis_inclusion"]["decision"] == "include"
    assert "preview_rows" not in region
    facts = context["sheets"][0]["business_facts"]
    assert facts["selected_records"] == [
        {
            "location": "데이터!A1",
            "region": "매출 현황",
            "values": [
                {
                    "cell": "A1",
                    "label": None,
                    "value": "Riot Games, Inc.",
                    "number_format": None,
                }
            ],
        }
    ]
    assert facts["selection_note"] == "원본 전체가 아닌 핵심 값 행만 선별한 결과"
    assert context["sheets"][0]["content_outline"] == {
        "sheet_role": None,
        "role_reasons": [],
        "region_titles": ["매출 현황"],
        "header_labels": ["부서"],
        "columns": [],
        "table_headers": [],
        "chart_titles": [],
    }


def test_prompt_prioritizes_workbook_subject_over_technical_counts() -> None:
    summary = WorkbookSummary(filename="매출.xlsx", sheet_count=0, sheets=[])

    prompt = build_user_prompt(summary)

    assert "분석 대상의 현재 상태" in prompt
    assert "대상·출처·시점·수치·비교" in prompt
    assert "데이터 목록 설명은 금지" in prompt
