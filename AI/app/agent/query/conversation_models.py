"""Bounded referent hints, never previous answer prose or factual evidence."""
from typing import Annotated, Literal, Protocol

from pydantic import BaseModel, ConfigDict, Field, StringConstraints
from app.agent.query.clarification_models import SourceClarificationSelection

Reference = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=200)]
Question = Annotated[str, StringConstraints(strip_whitespace=True, min_length=2, max_length=1000)]
Label = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=200)]


class ConversationTurn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    question: Question
    evidence: list[Reference] = Field(default_factory=list, max_length=12)
    needs_clarification: bool = False


class ConversationInsight(BaseModel):
    model_config = ConfigDict(extra="forbid")
    title: Label
    topic: Label | None = None
    evidence: list[Reference] = Field(default_factory=list, max_length=12)


class QuestionConversation(BaseModel):
    model_config = ConfigDict(extra="forbid")
    turns: list[ConversationTurn] = Field(default_factory=list, max_length=6)
    insights: list[ConversationInsight] = Field(default_factory=list, max_length=6)
    selection: SourceClarificationSelection | None = None


class ContextResolutionDraft(BaseModel):
    model_config = ConfigDict(extra="forbid")
    status: Literal["standalone", "resolved", "ambiguous"]
    question: Question | None = None
    context_ids: list[Label] = Field(default_factory=list, max_length=6,
                                   description="Input item IDs such as turn:0 or insight:0; never cell addresses")


class QuestionContextResolver(Protocol):
    async def resolve(self, question: str, context: list[dict]) -> ContextResolutionDraft: ...
