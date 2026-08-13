from typing import Annotated

from fastapi import APIRouter, File, HTTPException, UploadFile, status
from pydantic import BaseModel, ConfigDict

from app.services.workbook_parser import InvalidWorkbookError, parse_workbook

router = APIRouter(prefix="/api/v1/workbooks", tags=["workbooks"])

MAX_FILE_SIZE_BYTES = 50 * 1024 * 1024
READ_CHUNK_SIZE = 1024 * 1024


class CellRegionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    start_cell: str
    end_cell: str
    cell_count: int


class SheetSummaryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    name: str
    rows: int
    columns: int
    formula_count: int
    table_count: int
    chart_count: int
    region_count: int
    regions: list[CellRegionResponse]


class WorkbookSummaryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    filename: str
    sheet_count: int
    sheets: list[SheetSummaryResponse]


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
