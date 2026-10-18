"""A source choice is a bounded question, never client-provided factual data."""
from typing import Annotated

from pydantic import BaseModel, ConfigDict, StringConstraints

ChoiceId = Annotated[str, StringConstraints(pattern=r"^[0-9a-f]{64}$")]
ChoiceQuestion = Annotated[str, StringConstraints(min_length=2, max_length=1000)]
ChoiceLabel = Annotated[str, StringConstraints(min_length=1, max_length=200)]


class SourceClarificationOption(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: ChoiceId
    label: ChoiceLabel
    scope: ChoiceLabel
    details: Annotated[str, StringConstraints(max_length=1000)]
    question: ChoiceQuestion


class SourceClarificationSelection(BaseModel):
    model_config = ConfigDict(extra="forbid")
    source_question: ChoiceQuestion
    option_id: ChoiceId
