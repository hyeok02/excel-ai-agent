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
from app.api.workbook_models.provenance import ProvenanceResponse
from app.services.insights.models import ValidatedWorkbookInsightReport


class FormulaAnalysisResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    cell: str
    formula: str
    references: list[str]
    cached_value: str | int | float | bool | None
    role: str
    provenance: ProvenanceResponse | None = None


class FormulaRiskImpactResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    affected_formula_count: int
    affected_sheet_count: int
    affected_sheets: list[str]
    max_depth: int
    risk_score: int
    risk_level: str


class FormulaRiskFindingResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    kind: str
    severity: str
    sheet_name: str
    cell: str
    message: str
    formula: str
    reference: str | None = None
    function_name: str | None = None
    observed_value: str | int | float | bool | None = None
    provenance: ProvenanceResponse | None = None
    impact: FormulaRiskImpactResponse | None = None


class FormulaRiskSummaryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    total_count: int
    error_count: int
    warning_count: int
    broken_reference_count: int
    missing_sheet_count: int
    external_reference_count: int
    dynamic_function_count: int
    pattern_mismatch_count: int
    hardcoded_value_count: int
    high_risk_count: int
    critical_risk_count: int
    findings: list[FormulaRiskFindingResponse]


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
    formula_risk_summary: FormulaRiskSummaryResponse


class WorkbookInsightsResponse(BaseModel):
    workbook: WorkbookSummaryResponse
    report: ValidatedWorkbookInsightReport
