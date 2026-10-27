"""A model proposes bounded original clauses, never rewritten answer facts."""
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field
from app.agent.query.tabular_query_models import TabularQueryPlan
from app.agent.query.relational_models import RelationalQueryPlan
from app.agent.query.header_relation_models import HeaderRelationPlan


class CompositeQuestionPart(BaseModel):
    model_config = ConfigDict(extra="forbid")

    source_text: str = Field(min_length=1, max_length=1000)
    scope: Literal["whole_workbook", "specific"] = "specific"
    kind: Literal["summary", "brief", "structure", "comparison", "row_list", "row_count",
                  "cell_lookup", "formula_risk", "aggregation", "field_relation", "other"] = "other"
    targets: list[str] = Field(default_factory=list, max_length=6)
    tabular_query: TabularQueryPlan | None = None
    relational_query: RelationalQueryPlan | None = None
    header_relation: HeaderRelationPlan | None = None


class CompositeQueryPlan(BaseModel):
    model_config = ConfigDict(extra="forbid")

    shared_prefix: str = Field(default="", max_length=1000)
    parts: list[CompositeQuestionPart] = Field(min_length=2, max_length=4)
