from typing import Annotated

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from pydantic import BaseModel, ConfigDict

from app.services.insight_generator import (
    InsightConfigurationError,
    InsightGenerationError,
    InsightGenerator,
    LangChainInsightGenerator,
    WorkbookInsightReport,
)
from app.services.workbook_parser import InvalidWorkbookError, parse_workbook

router = APIRouter(prefix="/api/v1/workbooks", tags=["workbooks"])

MAX_FILE_SIZE_BYTES = 50 * 1024 * 1024
READ_CHUNK_SIZE = 1024 * 1024


class CellRegionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    start_cell: str
    end_cell: str
    cell_count: int
    title: str | None
    row_count: int
    column_count: int
    merged_ranges: list[str]
    header_paths: list["HeaderPathResponse"]
    preview_rows: list[list["CellSnapshotResponse"]]
    is_truncated: bool


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


class HeaderPathResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    column: str
    labels: list[str]


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
    tables: list[TableSummaryResponse]
    charts: list[ChartSummaryResponse]


class DependencyNodeResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    label: str
    sheet: str | None
    cell: str | None
    kind: str
    formula: str | None


class DependencyEdgeResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    source: str
    target: str
    reference: str
    cross_sheet: bool


class DependencyClusterResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    node_count: int
    edge_count: int
    formula_count: int
    sheet_names: list[str]
    nodes: list[DependencyNodeResponse]
    edges: list[DependencyEdgeResponse]
    is_truncated: bool


class DependencySummaryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    node_count: int
    edge_count: int
    formula_node_count: int
    cross_sheet_edge_count: int
    named_reference_count: int
    external_reference_count: int
    cluster_count: int
    clusters: list[DependencyClusterResponse]


class WorkbookSummaryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    filename: str
    sheet_count: int
    sheets: list[SheetSummaryResponse]
    dependency_summary: DependencySummaryResponse


class WorkbookInsightsResponse(BaseModel):
    workbook: WorkbookSummaryResponse
    report: WorkbookInsightReport


def get_insight_generator() -> InsightGenerator:
    try:
        return LangChainInsightGenerator.from_environment()
    except InsightConfigurationError as exception:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exception),
        ) from exception


async def read_upload(upload: UploadFile) -> bytes:
    chunks: list[bytes] = []
    total_size = 0

    while chunk := await upload.read(READ_CHUNK_SIZE):
        total_size += len(chunk)
        if total_size > MAX_FILE_SIZE_BYTES:
            raise HTTPException(
                status_code=status.HTTP_413_CONTENT_TOO_LARGE,
                detail="파일 크기는 50MB를 초과할 수 없습니다.",
            )
        chunks.append(chunk)

    if total_size == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="빈 파일은 업로드할 수 없습니다.",
        )

    return b"".join(chunks)


@router.post("/summary", response_model=WorkbookSummaryResponse)
async def summarize_workbook(
    file: Annotated[UploadFile, File(description="분석할 Excel 파일")],
) -> WorkbookSummaryResponse:
    content = await read_upload(file)

    try:
        summary = parse_workbook(file.filename or "", content)
    except InvalidWorkbookError as exception:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exception),
        ) from exception

    return WorkbookSummaryResponse.model_validate(summary)


@router.post("/insights", response_model=WorkbookInsightsResponse)
async def generate_workbook_insights(
    file: Annotated[UploadFile, File(description="인사이트를 생성할 Excel 파일")],
    insight_generator: Annotated[InsightGenerator, Depends(get_insight_generator)],
) -> WorkbookInsightsResponse:
    content = await read_upload(file)

    try:
        summary = parse_workbook(file.filename or "", content)
    except InvalidWorkbookError as exception:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exception),
        ) from exception

    try:
        report = await insight_generator.generate(summary)
    except InsightGenerationError as exception:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(exception),
        ) from exception

    return WorkbookInsightsResponse(
        workbook=WorkbookSummaryResponse.model_validate(summary),
        report=report,
    )
