from typing import Annotated

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status

from app.agent import AgentToolRegistry
from app.agent.query import (
    QuestionAnswer,
    WorkbookQuestionService,
    build_workbook_data_index,
)
from app.agent.query.generator import LangChainQuestionAnswerGenerator
from app.api.agent_tools import get_agent_tool_registry
from app.api.workbooks import _parse_or_bad_request, read_upload
from app.services.insights.models import (
    InsightConfigurationError,
    InsightGenerationError,
)

router = APIRouter(prefix="/api/v1/workbooks", tags=["workbooks"])


def get_question_answer_generator() -> LangChainQuestionAnswerGenerator:
    try:
        return LangChainQuestionAnswerGenerator.from_environment()
    except InsightConfigurationError as exception:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exception)
        ) from exception


@router.post("/questions", response_model=QuestionAnswer)
async def ask_workbook_question(
    question: Annotated[str, Form(min_length=2, max_length=1000)],
    file: Annotated[UploadFile, File(description="질문할 Excel 파일")],
    generator: Annotated[LangChainQuestionAnswerGenerator, Depends(get_question_answer_generator)],
    registry: Annotated[AgentToolRegistry, Depends(get_agent_tool_registry)],
) -> QuestionAnswer:
    content = await read_upload(file)
    summary = _parse_or_bad_request(file.filename or "", content)
    included_sheets = {sheet.name for sheet in summary.sheets}
    data_index = build_workbook_data_index(summary.filename, content, included_sheets)
    try:
        return await WorkbookQuestionService(generator, registry).answer(
            question, summary, data_index
        )
    except InsightGenerationError as exception:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(exception)
        ) from exception
