from app.services.analysis_strategy import (
    AnalysisDepth,
    AnalysisStrategy,
    select_analysis_profile,
)
from app.services.workbook_parser import SheetSummary, WorkbookSummary


def create_summary(
    *,
    sheet_count: int = 1,
    formula_count: int = 0,
) -> WorkbookSummary:
    sheets = [
        SheetSummary(
            name=f"Sheet{index + 1}",
            rows=100,
            columns=10,
            formula_count=formula_count,
            table_count=0,
            chart_count=0,
            formulas=[],
            region_count=1,
            regions=[],
        )
        for index in range(sheet_count)
    ]
    return WorkbookSummary(
        filename="analysis.xlsx",
        sheet_count=sheet_count,
        sheets=sheets,
    )


def test_auto_selects_fast_profile_for_simple_workbook() -> None:
    profile = select_analysis_profile(create_summary(), AnalysisDepth.AUTO)

    assert profile.strategy == AnalysisStrategy.FAST


def test_auto_selects_standard_profile_for_complex_workbook() -> None:
    profile = select_analysis_profile(
        create_summary(sheet_count=12, formula_count=1000),
        AnalysisDepth.AUTO,
    )

    assert profile.strategy == AnalysisStrategy.STANDARD


def test_precise_depth_always_selects_precise_profile() -> None:
    profile = select_analysis_profile(create_summary(), AnalysisDepth.PRECISE)

    assert profile.strategy == AnalysisStrategy.PRECISE
