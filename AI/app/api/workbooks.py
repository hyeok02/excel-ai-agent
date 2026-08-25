from typing import Annotated

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status

from app.api.workbook_models import (
    SemanticClassificationResponse,
    WorkbookInsightsResponse,
    WorkbookSummaryResponse,
)
from app.services.analysis_strategy import AnalysisDepth
from app.services.insight_generator import (
    InsightConfigurationError,
    InsightGenerationError,
    InsightGenerator,
    LangChainInsightGenerator,
)
from app.services.workbook_parser import InvalidWorkbookError, parse_workbook

router = APIRouter(prefix="/api/v1/workbooks", tags=["workbooks"])
MAX_FILE_SIZE_BYTES = 50 * 1024 * 1024
READ_CHUNK_SIZE = 1024 * 1024


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
    summary = _parse_or_bad_request(file.filename or "", await read_upload(file))
    return WorkbookSummaryResponse.model_validate(summary)


@router.post("/insights", response_model=WorkbookInsightsResponse)
async def generate_workbook_insights(
    file: Annotated[UploadFile, File(description="인사이트를 생성할 Excel 파일")],
    insight_generator: Annotated[InsightGenerator, Depends(get_insight_generator)],
    depth: Annotated[
        AnalysisDepth,
        Form(description="분석 깊이: AUTO, FAST, PRECISE"),
    ] = AnalysisDepth.AUTO,
) -> WorkbookInsightsResponse:
    summary = _parse_or_bad_request(file.filename or "", await read_upload(file))
    try:
        report = await insight_generator.generate(summary, depth)
    except InsightGenerationError as exception:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(exception),
        ) from exception
    return WorkbookInsightsResponse(
        workbook=WorkbookSummaryResponse.model_validate(summary),
        report=report,
    )


def _parse_or_bad_request(filename: str, content: bytes):
    try:
        return parse_workbook(filename, content)
    except InvalidWorkbookError as exception:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exception),
        ) from exception


__all__ = [
    "SemanticClassificationResponse",
    "get_insight_generator",
    "router",
]
