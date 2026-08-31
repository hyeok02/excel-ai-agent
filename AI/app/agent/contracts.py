from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from enum import StrEnum
from typing import TYPE_CHECKING, Any, Protocol

from app.services.provenance import AnalysisEvidence
from app.services.workbook_parsing.models import WorkbookSummary

if TYPE_CHECKING:
    from app.agent.query.index import WorkbookDataIndex

ToolArguments = Mapping[str, Any]


class ToolCategory(StrEnum):
    SEMANTIC = "semantic"
    DEPENDENCY = "dependency"
    VALIDATION = "validation"


class InvalidToolArgumentsError(ValueError):
    """Raised when an Agent Tool receives unsupported arguments."""


@dataclass(frozen=True)
class AgentToolMetadata:
    name: str
    description: str
    category: ToolCategory
    capabilities: tuple[str, ...]
    input_schema: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.name.strip() or not self.description.strip():
            raise ValueError("Agent Tool 이름과 설명은 비어 있을 수 없습니다.")
        if not self.capabilities:
            raise ValueError("Agent Tool에는 하나 이상의 기능 설명이 필요합니다.")


@dataclass(frozen=True)
class AgentToolContext:
    workbook: WorkbookSummary
    data_index: WorkbookDataIndex | None = None


@dataclass(frozen=True)
class AgentToolResult:
    tool_name: str
    summary: str
    data: Mapping[str, Any]
    evidence: tuple[AnalysisEvidence, ...] = ()


class AgentTool(Protocol):
    @property
    def metadata(self) -> AgentToolMetadata: ...

    def execute(
        self,
        context: AgentToolContext,
        arguments: ToolArguments | None = None,
    ) -> AgentToolResult: ...
