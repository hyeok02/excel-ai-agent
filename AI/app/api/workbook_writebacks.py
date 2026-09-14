from io import BytesIO
from typing import Annotated
from zipfile import ZIP_DEFLATED, ZipFile

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from fastapi.concurrency import run_in_threadpool
from pydantic import TypeAdapter, ValidationError

from app.agent.query import build_workbook_data_index
from app.agent.writeback import (
    LangChainWritebackGenerator,
    WorkbookWritebackProposalService,
    WritebackChange,
    WritebackProposal,
    apply_writeback,
)
from app.agent.writeback.editor import UnsafeWritebackError
from app.api.workbooks import parse_or_bad_request, read_upload
from app.services.insights.models import InsightConfigurationError, InsightGenerationError

router = APIRouter(prefix="/api/v1/workbooks", tags=["workbooks"])


def get_writeback_generator() -> LangChainWritebackGenerator:
    try:
        return LangChainWritebackGenerator.from_environment()
    except InsightConfigurationError as exception:
        raise HTTPException(status_code=503, detail=str(exception)) from exception


@router.post("/writeback-proposals", response_model=WritebackProposal)
async def propose_writeback(
    instruction: Annotated[str, Form(min_length=2, max_length=1000)],
    file: Annotated[UploadFile, File(description="수정할 원본 Excel 파일")],
    generator: Annotated[LangChainWritebackGenerator, Depends(get_writeback_generator)],
) -> WritebackProposal:
    content = await read_upload(file)
    summary = await parse_or_bad_request(file.filename or "", content)
    included = {sheet.name for sheet in summary.sheets}
    index = await run_in_threadpool(
        build_workbook_data_index, summary.filename, content, included
    )
    try:
        return await WorkbookWritebackProposalService(generator).propose(instruction, index)
    except InsightGenerationError as exception:
        raise HTTPException(status_code=502, detail=str(exception)) from exception


@router.post("/writebacks/apply")
async def apply_approved_writeback(
    changes: Annotated[str, Form(min_length=2)],
    file: Annotated[UploadFile, File(description="수정할 원본 Excel 파일")],
):
    content = await read_upload(file)
    await parse_or_bad_request(file.filename or "", content)
    try:
        parsed = TypeAdapter(list[WritebackChange]).validate_json(changes)
        archive = await run_in_threadpool(
            _build_writeback_archive, file.filename or "workbook.xlsx", content, parsed
        )
        return _zip_response(archive)
    except (ValidationError, UnsafeWritebackError) as exception:
        raise HTTPException(status_code=422, detail=str(exception)) from exception


def _build_writeback_archive(
    filename: str, content: bytes, changes: list[WritebackChange]
) -> bytes:
    modified, manifest = apply_writeback(filename, content, changes)
    archive = BytesIO()
    extension = filename.rsplit(".", 1)[-1].lower()
    with ZipFile(archive, "w", ZIP_DEFLATED) as package:
        package.writestr(f"workbook.{extension}", modified)
        package.writestr("manifest.json", manifest.model_dump_json())
    return archive.getvalue()


def _zip_response(content: bytes):
    from fastapi.responses import Response

    return Response(content, media_type="application/zip")
