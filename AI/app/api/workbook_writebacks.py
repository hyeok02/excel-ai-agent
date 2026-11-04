import math
from io import BytesIO
from typing import Annotated
from zipfile import ZIP_DEFLATED, ZipFile

from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile
from starlette.datastructures import UploadFile as StarletteUploadFile
from starlette.formparsers import MultiPartException
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
from app.agent.writeback.pivot_notice import with_pivot_notice
from app.api.workbooks import HIDDEN_SHEETS, parse_or_bad_request, read_upload
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
    include_hidden_sheets: Annotated[bool, Form(description=HIDDEN_SHEETS)] = False,
) -> WritebackProposal:
    content = await read_upload(file)
    summary = await parse_or_bad_request(
        file.filename or "", content, include_hidden_sheets
    )
    included = {sheet.name for sheet in summary.sheets}
    # An edit must reach every row it names, so the index is not cut at the question budget.
    index = await run_in_threadpool(
        build_workbook_data_index, summary.filename, content, included, math.inf, math.inf
    )
    try:
        proposal = await WorkbookWritebackProposalService(generator).propose(instruction, index, summary)
        return with_pivot_notice(proposal, content)
    except InsightGenerationError as exception:
        raise HTTPException(status_code=502, detail=str(exception)) from exception


# The approved change list grows with the rows a rule reaches; Starlette's 1MB
# default for a form field would refuse a few thousand rows.
CHANGES_FIELD_BYTES = 512 * 1024 * 1024


@router.post("/writebacks/apply")
async def apply_approved_writeback(request: Request):
    try:
        form = await request.form(max_part_size=CHANGES_FIELD_BYTES)
    except MultiPartException as exception:
        raise HTTPException(status_code=400, detail=exception.message) from exception
    changes, file = form.get("changes"), form.get("file")
    if not isinstance(changes, str) or len(changes) < 2 or not isinstance(file, StarletteUploadFile):
        raise HTTPException(status_code=422, detail="승인한 변경 목록과 원본 Excel 파일이 필요합니다.")
    include_hidden_sheets = str(form.get("include_hidden_sheets", "")).casefold() in {"true", "1", "on", "yes"}
    content = await read_upload(file)
    await parse_or_bad_request(file.filename or "", content, include_hidden_sheets)
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
