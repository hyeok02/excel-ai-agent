from typing import Any

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from app.agent import AgentToolRegistry, ToolCategory, create_default_tool_registry

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
