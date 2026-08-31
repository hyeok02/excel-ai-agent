from datetime import datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict

from app.agent.planning.models import AgentExecutionPlan
from app.services.provenance import EvidenceKind


class AgentExecutionStatus(StrEnum):
    SUCCEEDED = "succeeded"
    PARTIAL = "partial"
    FAILED = "failed"


class AgentStepStatus(StrEnum):
    PENDING = "pending"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    SKIPPED = "skipped"


class AgentStepError(BaseModel):
    code: str
    message: str
    retryable: bool = False


class AgentExecutionEvidence(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    kind: EvidenceKind
    sheet_name: str
    reference: str | None
    description: str
    value: str | int | float | bool | None = None
    formula: str | None = None


class AgentToolExecutionResult(BaseModel):
    summary: str
    data: dict[str, Any]
    evidence: list[AgentExecutionEvidence]


class AgentStepExecution(BaseModel):
    step_id: str
    title: str
    tool_name: str
    purpose: str
    expected_output: str
    status: AgentStepStatus
    started_at: datetime | None = None
    completed_at: datetime | None = None
    result: AgentToolExecutionResult | None = None
    error: AgentStepError | None = None


class AgentExecution(BaseModel):
    execution_id: str
    status: AgentExecutionStatus
    summary: str
    started_at: datetime
    completed_at: datetime
    succeeded_step_count: int
    failed_step_count: int
    skipped_step_count: int
    plan: AgentExecutionPlan
    steps: list[AgentStepExecution]
