from pydantic import BaseModel, ConfigDict

from app.api.workbook_models.dependencies import DependencySummaryResponse
from app.api.workbook_models.details import (
    CellRegionResponse,
    ChartSummaryResponse,
    ColumnSchemaResponse,
    TableSummaryResponse,
)
from app.api.workbook_models.semantic import (
    AnalysisInclusionResponse,
    SheetClassificationResponse,
)
from app.services.insight_generator import WorkbookInsightReport


class FormulaAnalysisResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    cell: str
    formula: str
    references: list[str]
    cached_value: str | int | float | bool | None
    role: str


class SheetSummaryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    name: str
    rows: int
    columns: int
    formula_count: int
    table_count: int
    chart_count: int
    formulas: list[FormulaAnalysisResponse]
    region_count: int
    regions: list[CellRegionResponse]
    column_schemas: list[ColumnSchemaResponse]
    analysis_inclusion: AnalysisInclusionResponse
    sheet_classification: SheetClassificationResponse
    tables: list[TableSummaryResponse]
    charts: list[ChartSummaryResponse]


class ExcludedSheetSummaryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    name: str
    state: str
    analysis_inclusion: AnalysisInclusionResponse
    sheet_classification: SheetClassificationResponse


class WorkbookSummaryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    filename: str
    sheet_count: int
    sheets: list[SheetSummaryResponse]
    total_sheet_count: int
    excluded_sheet_count: int
    excluded_sheets: list[ExcludedSheetSummaryResponse]
    dependency_summary: DependencySummaryResponse


class WorkbookInsightsResponse(BaseModel):
    workbook: WorkbookSummaryResponse
    report: WorkbookInsightReport
