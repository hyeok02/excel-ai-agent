from enum import StrEnum
from typing import Protocol

from pydantic import BaseModel, Field

from app.agent.execution.models import AgentExecutionEvidence


class QuestionAnswerStatus(StrEnum):
    ANSWERED = "answered"
    LIMITED = "limited"
    INSUFFICIENT_EVIDENCE = "insufficient_evidence"


class QuestionAnswerDraft(BaseModel):
    answer: str = Field(min_length=1, max_length=4000)
    evidence: list[str] = Field(default_factory=list, max_length=12)
    confidence: float = Field(ge=0, le=1)
    limitations: list[str] = Field(default_factory=list, max_length=5)


class QuestionAnswerEvidence(AgentExecutionEvidence):
    label: str


class QuestionAnswer(BaseModel):
    question: str
    answer: str
    status: QuestionAnswerStatus
    confidence: float = Field(ge=0, le=1)
    selected_tools: list[str]
    evidence: list[QuestionAnswerEvidence]
    limitations: list[str]


class QuestionAnswerGenerator(Protocol):
    async def generate(
        self, question: str, filename: str, execution_context: dict[str, object]
    ) -> QuestionAnswerDraft: ...
