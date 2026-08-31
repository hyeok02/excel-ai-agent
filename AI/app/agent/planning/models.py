from enum import StrEnum
from typing import Literal, Protocol

from pydantic import BaseModel, Field, model_validator

from app.agent.contracts import AgentToolMetadata
from app.services.workbook_parsing.models import WorkbookSummary


class StepFailurePolicy(StrEnum):
    STOP = "stop"
    CONTINUE = "continue"


class AgentPlanStep(BaseModel):
    id: str = Field(pattern=r"^step_[1-9][0-9]*$")
    title: str = Field(min_length=2, max_length=80)
    tool_name: str = Field(min_length=1, max_length=100)
    arguments: dict[str, object] = Field(default_factory=dict)
    purpose: str = Field(
        min_length=5, max_length=300, description="이 도구로 확인할 업무 질문"
    )
    rationale: str = Field(
        min_length=5, max_length=300, description="이 단계가 사용자 목표에 필요한 이유"
    )
    expected_output: str = Field(
        min_length=5, max_length=300, description="사용자가 이 단계에서 얻게 될 결과"
    )
    evidence_required: list[str] = Field(min_length=1, max_length=5)
    depends_on: list[str] = Field(default_factory=list, max_length=7)
    on_failure: StepFailurePolicy = StepFailurePolicy.STOP


class AgentExecutionPlan(BaseModel):
    schema_version: Literal["1.0"] = "1.0"
    user_intent: str = Field(min_length=2, max_length=1000)
    objective: str = Field(min_length=5, max_length=500)
    user_value: str = Field(
        min_length=5,
        max_length=500,
        description="원본 Excel을 직접 보는 것보다 빠르게 알 수 있는 내용",
    )
    expected_deliverable: str = Field(min_length=5, max_length=500)
    steps: list[AgentPlanStep] = Field(min_length=1, max_length=8)
    success_criteria: list[str] = Field(min_length=1, max_length=6)
    assumptions: list[str] = Field(default_factory=list, max_length=5)
    limitations: list[str] = Field(default_factory=list, max_length=5)

    @model_validator(mode="after")
    def validate_step_graph(self) -> "AgentExecutionPlan":
        seen: set[str] = set()
        for step in self.steps:
            if step.id in seen:
                raise ValueError(f"중복된 계획 단계 ID입니다: {step.id}")
            unknown = [dependency for dependency in step.depends_on if dependency not in seen]
            if unknown:
                raise ValueError(
                    f"{step.id}의 선행 단계는 앞서 정의되어야 합니다: {', '.join(unknown)}"
                )
            seen.add(step.id)
        return self


class PlannerConfigurationError(RuntimeError):
    """Raised when Planner configuration is missing or invalid."""


class PlanGenerationError(RuntimeError):
    """Raised when a validated execution plan cannot be generated."""


class AgentPlanner(Protocol):
    async def create_plan(
        self,
        intent: str,
        summary: WorkbookSummary,
        tools: tuple[AgentToolMetadata, ...],
    ) -> AgentExecutionPlan: ...
