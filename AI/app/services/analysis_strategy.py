from dataclasses import dataclass
from enum import StrEnum

from app.services.workbook_parser import WorkbookSummary


class AnalysisDepth(StrEnum):
    AUTO = "AUTO"
    FAST = "FAST"
    PRECISE = "PRECISE"


class AnalysisStrategy(StrEnum):
    FAST = "FAST"
    STANDARD = "STANDARD"
    PRECISE = "PRECISE"


@dataclass(frozen=True)
class AnalysisProfile:
    strategy: AnalysisStrategy
    model_env_name: str
    default_model: str
    max_sheets: int
    max_formulas_per_sheet: int
    max_regions_per_sheet: int
    max_tables_per_sheet: int
    max_charts_per_sheet: int
    max_insights: int
    max_completion_tokens: int


FAST_PROFILE = AnalysisProfile(
    strategy=AnalysisStrategy.FAST,
    model_env_name="OPENAI_FAST_MODEL",
    default_model="gpt-4.1-nano",
    max_sheets=10,
    max_formulas_per_sheet=4,
    max_regions_per_sheet=3,
    max_tables_per_sheet=3,
    max_charts_per_sheet=3,
    max_insights=3,
    max_completion_tokens=900,
)

STANDARD_PROFILE = AnalysisProfile(
    strategy=AnalysisStrategy.STANDARD,
    model_env_name="OPENAI_STANDARD_MODEL",
    default_model="gpt-4.1-mini",
    max_sheets=20,
    max_formulas_per_sheet=8,
    max_regions_per_sheet=6,
    max_tables_per_sheet=5,
    max_charts_per_sheet=5,
    max_insights=4,
    max_completion_tokens=1600,
)

PRECISE_PROFILE = AnalysisProfile(
    strategy=AnalysisStrategy.PRECISE,
    model_env_name="OPENAI_PRECISE_MODEL",
    default_model="gpt-4.1",
    max_sheets=40,
    max_formulas_per_sheet=16,
    max_regions_per_sheet=10,
    max_tables_per_sheet=8,
    max_charts_per_sheet=8,
    max_insights=5,
    max_completion_tokens=2500,
)


def calculate_complexity_score(summary: WorkbookSummary) -> int:
    formula_count = sum(sheet.formula_count for sheet in summary.sheets)
    region_count = sum(sheet.region_count for sheet in summary.sheets)
    table_and_chart_count = sum(
        sheet.table_count + sheet.chart_count for sheet in summary.sheets
    )
    dependencies = summary.dependency_summary

    score = 0
    score += min(summary.sheet_count, 12) * 2
    score += min(formula_count // 250, 24)
    score += min(region_count // 20, 10)
    score += min(table_and_chart_count, 8)
    score += min(dependencies.edge_count // 500, 18)
    score += min(dependencies.cross_sheet_edge_count // 100, 12)
    score += min(dependencies.external_reference_count * 3, 12)
    score += min(dependencies.named_reference_count // 20, 6)
    return score


def select_analysis_profile(
    summary: WorkbookSummary,
    requested_depth: AnalysisDepth,
) -> AnalysisProfile:
    if requested_depth == AnalysisDepth.FAST:
        return FAST_PROFILE
    if requested_depth == AnalysisDepth.PRECISE:
        return PRECISE_PROFILE

    # 자동 분석은 사용자가 예상하지 못한 장시간 작업을 피하기 위해
    # 빠른 분석과 표준 분석 중에서만 워크북 복잡도에 맞춰 선택한다.
    if calculate_complexity_score(summary) < 24:
        return FAST_PROFILE
    return STANDARD_PROFILE
