from typing import Annotated

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from pydantic import ValidationError

from app.agent import (
    AgentExecution,
    AgentExecutionPlan,
    AgentToolContext,
    AgentToolExecutor,
    AgentToolRegistry,
    PlanGenerationError,
)
from app.agent.planning import ensure_executable_plan
from app.agent.query import build_workbook_data_index
from app.api.agent_tools import get_agent_tool_registry
from app.api.workbooks import _parse_or_bad_request, read_upload

router = APIRouter(prefix="/api/v1/agent", tags=["agent"])


def get_agent_executor() -> AgentToolExecutor:
    return AgentToolExecutor()


@router.post("/executions", response_model=AgentExecution)
async def execute_agent_plan(
    plan: Annotated[str, Form(description="Agent Planner가 생성한 JSON 실행 계획")],
    file: Annotated[UploadFile, File(description="도구를 실행할 Excel 파일")],
    executor: Annotated[AgentToolExecutor, Depends(get_agent_executor)],
    registry: Annotated[AgentToolRegistry, Depends(get_agent_tool_registry)],
) -> AgentExecution:
    execution_plan = _parse_plan(plan, registry)
    content = await read_upload(file)
    summary = _parse_or_bad_request(file.filename or "", content)
    included_sheets = {sheet.name for sheet in summary.sheets}
    data_index = build_workbook_data_index(
        summary.filename, content, included_sheets
    )
    return executor.execute(
        execution_plan,
        AgentToolContext(summary, data_index),
        registry,
    )


def _parse_plan(raw_plan: str, registry: AgentToolRegistry) -> AgentExecutionPlan:
    try:
        plan = AgentExecutionPlan.model_validate_json(raw_plan)
        return ensure_executable_plan(plan, registry.list_metadata())
    except (ValidationError, PlanGenerationError) as exception:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=f"실행 계획이 올바르지 않습니다: {exception}",
        ) from exception
