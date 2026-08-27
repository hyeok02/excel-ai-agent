from pydantic import BaseModel, ConfigDict

from app.api.workbook_models.semantic import (
    AnalysisInclusionResponse,
    SemanticClassificationResponse,
)
from app.api.workbook_models.provenance import ProvenanceResponse


class CellSnapshotResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    address: str
    value: str | int | float | bool | None
    formula: str | None
    cached_value: str | int | float | bool | None
    number_format: str | None
    bold: bool
    fill_color: str | None
    horizontal_alignment: str | None
    merged: bool
    semantic: SemanticClassificationResponse | None


class HeaderPathResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    column: str
    labels: list[str]


class ColumnSchemaResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    column: str
    source_range: str
    header_path: list[str]
    display_name: str
    standard_field: str
    data_type: str
    unit_type: str
    unit_label: str | None
    confidence: float
    evidence: list[str]
    provenance: ProvenanceResponse | None = None


class CellRegionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    start_cell: str
    end_cell: str
    cell_count: int
    title: str | None
    row_count: int
    column_count: int
    merged_ranges: list[str]
    header_paths: list[HeaderPathResponse]
    preview_rows: list[list[CellSnapshotResponse]]
    is_truncated: bool
    analysis_inclusion: AnalysisInclusionResponse
    semantic: SemanticClassificationResponse | None


class TableSummaryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    name: str
    display_name: str
    reference: str
    headers: list[str]
    row_count: int
    column_count: int
    preview_rows: list[list[CellSnapshotResponse]]
    is_truncated: bool


class ChartSeriesSummaryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    title: str | None
    categories_reference: str | None
    values_reference: str | None
    category_samples: list[str | int | float | bool | None]
    value_samples: list[str | int | float | bool | None]


class ChartSummaryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    title: str | None
    chart_type: str
    anchor_cell: str | None
    series_count: int
    series: list[ChartSeriesSummaryResponse]
    is_truncated: bool
