"""질문의 의도. 모델이 고르고, 실패하면 낱말 규칙이 대신한다."""
import re
from dataclasses import dataclass
from typing import Literal, Protocol

from pydantic import BaseModel, ConfigDict, Field

from app.agent.query.tabular_query_models import TabularQueryPlan
from app.agent.query.relational_models import RelationalQueryPlan
from app.agent.query.header_relation_models import HeaderRelationPlan
from app.agent.query.composite_models import CompositeQueryPlan
from app.agent.query.workbook_summary_rows import is_workbook_summary_question
from app.services.workbook_parsing.models import WorkbookSummary

MAX_TARGETS = 6


class QuestionIntentDraft(BaseModel):
    """모델은 연산과 카탈로그 ID만 선택하며 결과 숫자는 만들지 않는다."""

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
        "aggregation",
        "field_relation",
        "other",
    ]
    targets: list[str] = Field(default_factory=list, max_length=MAX_TARGETS)
    tabular_query: TabularQueryPlan | None = None
    relational_query: RelationalQueryPlan | None = None
    header_relation: HeaderRelationPlan | None = None
    composite_query: CompositeQueryPlan | None = None


@dataclass(frozen=True)
class QuestionIntent:
    whole_workbook: bool
    kind: str = "other"
    targets: tuple[str, ...] = ()
    from_model: bool = False
    tabular_query: TabularQueryPlan | None = None
    relational_query: RelationalQueryPlan | None = None
    header_relation: HeaderRelationPlan | None = None
    composite_query: CompositeQueryPlan | None = None

    @classmethod
    def from_draft(cls, draft: QuestionIntentDraft) -> "QuestionIntent":
        targets = tuple(
            text for value in draft.targets if (text := value.strip())
        )[:MAX_TARGETS]
        query = draft.tabular_query
        relational = draft.relational_query
        # A valid schema does not make an operation appropriate. A value lookup
        # or comparison cannot be answered by replacing it with a distribution.
        allowed = {
            "frequencies": {"aggregation", "summary", "row_count"},
            "numeric_summary": {"aggregation"},
            "row_count": {"row_count", "aggregation"},
            "distinct_count": {"row_count", "aggregation"},
            "lookup": {"cell_lookup"},
            "row_list": {"row_list"},
        }
        if query is not None and draft.kind not in allowed[query.operation]:
            query = None
        if relational is not None and draft.kind not in allowed[relational.operation]:
            relational = None
        if draft.tabular_query is not None and draft.relational_query is not None:
            query = relational = None
        relation = draft.header_relation if draft.kind == "field_relation" else None
        if draft.kind == "field_relation":
            query = relational = None
        return cls(
            draft.scope == "whole_workbook" and draft.kind != "field_relation"
            and not (draft.tabular_query or draft.relational_query or draft.composite_query),
            draft.kind, targets, True, query, relational, relation, draft.composite_query,
        )

    @classmethod
    def from_keywords(cls, question: str) -> "QuestionIntent":
        """모델을 부르지 못할 때. 서비스가 통째로 멈추는 것보다 낫다."""
        return cls(is_workbook_summary_question(question))

    @property
    def brief(self) -> bool:
        return self.kind == "brief"

    @property
    def wants_a_summary(self) -> bool:
        """응답 문체가 아니라, 실제 요청 범위가 파일 전체인 경우만 허용한다."""
        return self.whole_workbook and not (self.tabular_query or self.relational_query or self.composite_query)

    def enriched(self, question: str) -> str:
        """열 이름을 맞출 때 쓰는 글. 모델이 짚은 대상을 질문에 더해 준다."""
        # 사용자가 적은 식별자는 모델이 추측한 다른 행 이름으로 덮으면 안 된다.
        # 실제로 CVD #99 질문에 분류기가 CVD #2를 보태 정확히 그 행을 골랐다.
        if re.search(r"#\s*[0-9a-z]", question, re.I):
            return question
        return " ".join([question, *self.targets]) if self.targets else question


class QuestionIntentClassifier(Protocol):
    async def classify(
        self, question: str, summary: WorkbookSummary
    ) -> QuestionIntent: ...
