"""질문의 의도. 모델이 고르고, 실패하면 낱말 규칙이 대신한다."""
from dataclasses import dataclass
from typing import Literal, Protocol

from pydantic import BaseModel, ConfigDict, Field

from app.agent.query.workbook_summary_rows import is_workbook_summary_question
from app.services.workbook_parsing.models import WorkbookSummary

MAX_TARGETS = 6


class QuestionIntentDraft(BaseModel):
    """모델이 돌려주는 값. 숫자도 셀 주소도 모델에게 맡기지 않는다."""

    model_config = ConfigDict(extra="forbid")

    scope: Literal["whole_workbook", "specific"]
    kind: Literal[
        "summary",
        "brief",
        "structure",
        "comparison",
        "row_list",
        "row_count",
        "cell_lookup",
        "formula_risk",
        "other",
    ]
    targets: list[str] = Field(default_factory=list, max_length=MAX_TARGETS)


@dataclass(frozen=True)
class QuestionIntent:
    whole_workbook: bool
    kind: str = "other"
    targets: tuple[str, ...] = ()
    from_model: bool = False

    @classmethod
    def from_draft(cls, draft: QuestionIntentDraft) -> "QuestionIntent":
        targets = tuple(
            text for value in draft.targets if (text := value.strip())
        )[:MAX_TARGETS]
        return cls(draft.scope == "whole_workbook", draft.kind, targets, True)

    @classmethod
    def from_keywords(cls, question: str) -> "QuestionIntent":
        """모델을 부르지 못할 때. 서비스가 통째로 멈추는 것보다 낫다."""
        return cls(is_workbook_summary_question(question))

    @property
    def brief(self) -> bool:
        return self.kind == "brief"

    def enriched(self, question: str) -> str:
        """열 이름을 맞출 때 쓰는 글. 모델이 짚은 대상을 질문에 더해 준다."""
        return " ".join([question, *self.targets]) if self.targets else question


class QuestionIntentClassifier(Protocol):
    async def classify(
        self, question: str, summary: WorkbookSummary
    ) -> QuestionIntent: ...
