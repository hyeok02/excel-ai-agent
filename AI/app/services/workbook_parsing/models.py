from dataclasses import dataclass, field

from app.services.analysis_inclusion import (
    AnalysisInclusion,
    INCLUDED_BUSINESS_WORKSHEET,
)
from app.services.dependency_analyzer import DependencySummary
from app.services.formula_analyzer import FormulaAnalysis
from app.services.sheet_classifier import SheetClassification
from app.services.workbook_details import (
    ChartSummary,
    ColumnSchemaSummary,
    RegionSummary,
    TableSummary,
)


@dataclass(frozen=True)
class SheetSummary:
    name: str
    rows: int
    columns: int
    formula_count: int
    table_count: int
    chart_count: int
    formulas: list[FormulaAnalysis]
    region_count: int
    regions: list[RegionSummary]
    column_schemas: list[ColumnSchemaSummary] = field(default_factory=list)
    analysis_inclusion: AnalysisInclusion = INCLUDED_BUSINESS_WORKSHEET
    tables: list[TableSummary] = field(default_factory=list)
    charts: list[ChartSummary] = field(default_factory=list)
    sheet_classification: SheetClassification | None = None


@dataclass(frozen=True)
class ExcludedSheetSummary:
    name: str
    state: str
    analysis_inclusion: AnalysisInclusion
    sheet_classification: SheetClassification


@dataclass(frozen=True)
class WorkbookSummary:
    filename: str
    sheet_count: int
    sheets: list[SheetSummary]
    total_sheet_count: int = 0
    excluded_sheet_count: int = 0
    excluded_sheets: list[ExcludedSheetSummary] = field(default_factory=list)
    dependency_summary: DependencySummary = field(
        default_factory=DependencySummary.empty
    )
