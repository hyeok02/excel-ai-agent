"""A bounded query plan: the model selects source IDs; code computes values."""
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class TabularFilter(BaseModel):
    model_config = ConfigDict(extra="forbid")

    column_id: str
    operator: Literal["equals", "not_equals", "contains", "is_blank", "not_blank"]
    value: str | int | float | bool | None = None


class TabularQueryPlan(BaseModel):
    model_config = ConfigDict(extra="forbid")

    operation: Literal["frequencies", "numeric_summary", "row_count"]
    table_id: str
    column_scope: Literal["selected", "all_attributes"] = "selected"
    column_ids: list[str] = Field(default_factory=list, max_length=24)
    identity_column_ids: list[str] = Field(default_factory=list, max_length=24)
    filters: list[TabularFilter] = Field(default_factory=list, max_length=8)
