from typing import Annotated, Any

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from pydantic import BaseModel

from app.agent import (
    AgentExecutionPlan,
    AgentPlanner,
    AgentToolRegistry,
    LangChainAgentPlanner,
    PlanGenerationError,
    PlannerConfigurationError,
    ToolCategory,
    create_default_tool_registry,
)
from app.api.workbooks import _parse_or_bad_request, read_upload

router = APIRouter(prefix="/api/v1/agent", tags=["agent"])
_registry = create_default_tool_registry()


class AgentToolMetadataResponse(BaseModel):
    name: str
    description: str
    category: ToolCategory
    capabilities: list[str]
    input_schema: dict[str, Any]


def get_agent_tool_registry() -> AgentToolRegistry:
    return _registry


def get_agent_planner() -> AgentPlanner:
    try:
        return LangChainAgentPlanner.from_environment()
    except PlannerConfigurationError as exception:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exception),
        ) from exception


@router.get("/tools", response_model=list[AgentToolMetadataResponse])
def list_agent_tools(
    registry: AgentToolRegistry = Depends(get_agent_tool_registry),
) -> list[AgentToolMetadataResponse]:
    return [
        AgentToolMetadataResponse(
            name=metadata.name,
            description=metadata.description,
            category=metadata.category,
            capabilities=list(metadata.capabilities),
            input_schema=dict(metadata.input_schema),
        )
        for metadata in registry.list_metadata()
    ]


@router.post("/plans", response_model=AgentExecutionPlan)
async def create_agent_plan(
    intent: Annotated[
        str,
        Form(
            min_length=2,
            max_length=1000,
            description="이 Excel에서 확인하거나 결정하려는 업무 목적",
        ),
    ],
    file: Annotated[UploadFile, File(description="계획을 수립할 Excel 파일")],
    planner: Annotated[AgentPlanner, Depends(get_agent_planner)],
    registry: Annotated[AgentToolRegistry, Depends(get_agent_tool_registry)],
) -> AgentExecutionPlan:
    summary = _parse_or_bad_request(file.filename or "", await read_upload(file))
    try:
        return await planner.create_plan(intent, summary, registry.list_metadata())
    except PlanGenerationError as exception:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(exception),
        ) from exception
