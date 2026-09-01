from enum import StrEnum
from typing import Literal, Protocol

from pydantic import BaseModel, Field


class WritebackStatus(StrEnum):
    READY = "ready"
    BLOCKED = "blocked"


class WritebackChangeDraft(BaseModel):
    sheet_name: str = Field(min_length=1, max_length=100)
    reference: str = Field(min_length=2, max_length=50)
    new_value: str | int | float | bool | None
    reason: str = Field(min_length=1, max_length=500)


class WritebackContextCell(BaseModel):
    reference: str
    value: str | int | float | bool | None


class WritebackProposalDraft(BaseModel):
    summary: str = Field(min_length=1, max_length=1000)
    changes: list[WritebackChangeDraft] = Field(default_factory=list, max_length=50)
    limitations: list[str] = Field(default_factory=list, max_length=5)


class WritebackChange(WritebackChangeDraft):
    old_value: str | int | float | bool | None
    context_cells: list[WritebackContextCell] = Field(default_factory=list, max_length=5)
    change_type: Literal["value", "clear", "formula"] = "value"
    value_type: Literal["text", "number", "boolean", "date", "datetime", "blank", "formula"] = "text"
    affected_cells: list[str] = Field(default_factory=list, max_length=12)
    risk_level: Literal["low", "medium", "high"] = "low"


class WritebackProposal(BaseModel):
    instruction: str
    status: WritebackStatus
    summary: str
    changes: list[WritebackChange]
    risks: list[str]
    limitations: list[str]


class VerificationCheck(BaseModel):
    name: str
    passed: bool
    detail: str


class WritebackManifest(BaseModel):
    changed_cells: list[str]
    checks: list[VerificationCheck]
    verified: bool


class WritebackGenerator(Protocol):
    async def generate(
        self, instruction: str, filename: str, context: dict[str, object]
    ) -> WritebackProposalDraft: ...
