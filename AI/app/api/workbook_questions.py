from typing import Annotated

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from fastapi.concurrency import run_in_threadpool
from pydantic import ValidationError

from app.agent import AgentToolRegistry
from app.agent.query import (
    QuestionAnswer,
    WorkbookQuestionService,
    build_workbook_data_index,
)
from app.agent.query.generator import LangChainQuestionAnswerGenerator
from app.agent.query.intent_classifier import LangChainQuestionIntentClassifier
from app.agent.query.conversation_models import QuestionConversation
from app.agent.query.conversation_resolver import LangChainQuestionContextResolver
from app.api.agent_tools import get_agent_tool_registry
from app.api.workbooks import HIDDEN_SHEETS, parse_or_bad_request, read_upload
from app.services.insights.models import (
    InsightConfigurationError,
    InsightGenerationError,
)

router = APIRouter(prefix="/api/v1/workbooks", tags=["workbooks"])
# 분류기는 질문마다 새로 만들 이유가 없다. 캐시를 같이 쓴다.
_intent_classifier = LangChainQuestionIntentClassifier.from_environment()
_context_resolver = LangChainQuestionContextResolver.from_environment()


def get_question_context_resolver():
    return _context_resolver


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
    include_hidden_sheets: Annotated[bool, Form(description=HIDDEN_SHEETS)] = False,
    context: Annotated[str | None, Form(max_length=80_000)] = None,
    context_resolver=Depends(get_question_context_resolver),
) -> QuestionAnswer:
    try:
        conversation = QuestionConversation.model_validate_json(context) if context is not None else None
    except ValidationError as exception:
        raise HTTPException(status_code=422, detail="질문 맥락 형식이나 크기가 올바르지 않습니다.") from exception
    content = await read_upload(file)
    summary = await parse_or_bad_request(
        file.filename or "", content, include_hidden_sheets
    )
    included_sheets = {sheet.name for sheet in summary.sheets}
    data_index = await run_in_threadpool(
        build_workbook_data_index, summary.filename, content, included_sheets
    )
    try:
        return await WorkbookQuestionService(
            generator, registry, classifier=_intent_classifier, context_resolver=context_resolver
        ).answer(question, summary, data_index, conversation)
    except InsightGenerationError as exception:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exception)
        ) from exception
