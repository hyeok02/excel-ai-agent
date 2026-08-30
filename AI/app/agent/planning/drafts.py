from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.agent.planning.models import AgentExecutionPlan


class AgentPlanArgumentDraft(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=1, max_length=100)
    value: str | int | bool


class AgentPlanStepDraft(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str = Field(pattern=r"^step_[1-9][0-9]*$")
    title: str = Field(min_length=2, max_length=80)
    tool_name: str = Field(min_length=1, max_length=100)
    arguments: list[AgentPlanArgumentDraft]
    purpose: str = Field(min_length=5, max_length=300)
    rationale: str = Field(min_length=5, max_length=300)
    expected_output: str = Field(min_length=5, max_length=300)
    evidence_required: list[str] = Field(min_length=1, max_length=5)
    depends_on: list[str] = Field(max_length=7)

    @model_validator(mode="after")
    def validate_unique_arguments(self) -> "AgentPlanStepDraft":
        names = [argument.name for argument in self.arguments]
        if len(names) != len(set(names)):
            raise ValueError(f"{self.id}에 중복된 도구 인자가 있습니다.")
        return self


class AgentExecutionPlanDraft(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: Literal["1.0"]
    user_intent: str = Field(min_length=2, max_length=1000)
    objective: str = Field(min_length=5, max_length=500)
    user_value: str = Field(min_length=5, max_length=500)
    expected_deliverable: str = Field(min_length=5, max_length=500)
    steps: list[AgentPlanStepDraft] = Field(min_length=1, max_length=8)
    success_criteria: list[str] = Field(min_length=1, max_length=6)
    assumptions: list[str] = Field(max_length=5)
    limitations: list[str] = Field(max_length=5)

    def to_execution_plan(self, intent: str) -> AgentExecutionPlan:
        payload = self.model_dump()
        payload["user_intent"] = intent
        payload["steps"] = [
            {
                **step.model_dump(exclude={"arguments"}),
                "arguments": {
                    argument.name: argument.value for argument in step.arguments
                },
            }
            for step in self.steps
        ]
        return AgentExecutionPlan.model_validate(payload)
