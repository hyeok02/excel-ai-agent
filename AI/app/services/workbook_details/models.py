from dataclasses import dataclass
from typing import TypeAlias

from app.services.analysis_inclusion import (
    AnalysisInclusion,
    INCLUDED_POPULATED_REGION,
)
from app.services.semantic_models import SemanticClassification

CellValue: TypeAlias = str | int | float | bool | None


@dataclass(frozen=True)
class CellSnapshot:
    address: str
    value: CellValue
    formula: str | None
    cached_value: CellValue = None
    number_format: str | None = None
    bold: bool = False
    fill_color: str | None = None
    horizontal_alignment: str | None = None
    merged: bool = False
    semantic: SemanticClassification | None = None


@dataclass(frozen=True)
class HeaderPathSummary:
    column: str
    labels: list[str]


@dataclass(frozen=True)
class ColumnSchemaSummary:
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


@dataclass(frozen=True)
class RegionSummary:
    start_cell: str
    end_cell: str
    cell_count: int
    title: str | None
    row_count: int
    column_count: int
    merged_ranges: list[str]
    header_paths: list[HeaderPathSummary]
    preview_rows: list[list[CellSnapshot]]
    is_truncated: bool
    analysis_inclusion: AnalysisInclusion = INCLUDED_POPULATED_REGION
    semantic: SemanticClassification | None = None


@dataclass(frozen=True)
class TableSummary:
    name: str
    display_name: str
    reference: str
    headers: list[str]
    row_count: int
    column_count: int
    preview_rows: list[list[CellSnapshot]]
    is_truncated: bool


@dataclass(frozen=True)
class ChartSeriesSummary:
    title: str | None
    categories_reference: str | None
    values_reference: str | None
    category_samples: list[CellValue]
    value_samples: list[CellValue]


@dataclass(frozen=True)
class ChartSummary:
    title: str | None
    chart_type: str
    anchor_cell: str | None
    series_count: int
    series: list[ChartSeriesSummary]
    is_truncated: bool
