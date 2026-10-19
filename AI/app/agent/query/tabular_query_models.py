"""A bounded query plan: the model selects source IDs; code computes values."""
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class TabularFilter(BaseModel):
    model_config = ConfigDict(extra="forbid")

    column_id: str
    operator: Literal[
        "equals", "not_equals", "contains", "is_blank", "not_blank",
        "greater_than", "greater_than_or_equal", "less_than", "less_than_or_equal",
    ]
    value: str | int | float | bool | None = None
    value_unit: Literal["raw", "percent"] = "raw"


class TabularQueryPlan(BaseModel):
    model_config = ConfigDict(extra="forbid")

    operation: Literal["frequencies", "numeric_summary", "row_count", "lookup", "row_list"]
    table_id: str
    column_scope: Literal["selected", "all_attributes"] = "selected"
    column_ids: list[str] = Field(default_factory=list, max_length=24)
    group_by: list[str] = Field(default_factory=list, max_length=3)
    identity_column_ids: list[str] = Field(default_factory=list, max_length=24)
    filters: list[TabularFilter] = Field(default_factory=list, max_length=8)
    order_by: str | None = None
    descending: bool = True
    limit: int | None = Field(default=None, ge=1, le=100)
    statistic: Literal["all", "sum", "average", "min", "max"] = "all"
