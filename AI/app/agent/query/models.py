from enum import StrEnum
from typing import Protocol

from pydantic import BaseModel, Field

from app.agent.execution.models import AgentExecutionEvidence
from app.agent.query.claim_models import SourceClaim


class QuestionAnswerStatus(StrEnum):
    ANSWERED = "answered"
    LIMITED = "limited"
    INSUFFICIENT_EVIDENCE = "insufficient_evidence"


class QuestionVerificationLevel(StrEnum):
    UNVERIFIED = "unverified"
    SOURCE_CHECKED = "source_checked"
    REQUEST_CHECKED = "request_checked"


class QuestionAnswerVerification(BaseModel):
    """Record what was actually checked, independently of answer availability.

    Cited cells existing does not prove that the requested table, period or
    filters were selected. Only a deterministic, request-aligned execution may
    set REQUEST_CHECKED. Generated prose and legacy responses default to no
    such guarantee, including when their status is ``answered``.
    """

    level: QuestionVerificationLevel = QuestionVerificationLevel.UNVERIFIED
    checks: list[str] = Field(default_factory=list)


class QuestionAnswerDraft(BaseModel):
    answer: str = Field(min_length=1, max_length=4000)
    evidence: list[str] = Field(default_factory=list, max_length=12)
    confidence: float = Field(ge=0, le=1)
    limitations: list[str] = Field(default_factory=list, max_length=5)
    claims: list[SourceClaim] = Field(default_factory=list, max_length=12)


class QuestionAnswerEvidence(AgentExecutionEvidence):
    label: str


class QuestionAnswer(BaseModel):
    question: str
    resolved_question: str | None = None
    answer: str
    status: QuestionAnswerStatus
    confidence: float = Field(ge=0, le=1)
    selected_tools: list[str]
    evidence: list[QuestionAnswerEvidence]
    limitations: list[str]
    verification: QuestionAnswerVerification = Field(default_factory=QuestionAnswerVerification)


class QuestionAnswerGenerator(Protocol):
    async def generate(
        self, question: str, filename: str, execution_context: dict[str, object]
    ) -> QuestionAnswerDraft: ...
