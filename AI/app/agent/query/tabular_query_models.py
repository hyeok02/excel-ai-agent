"""A bounded query plan: the model selects source IDs; code computes values."""
import math
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.agent.query.boolean_filter_models import BooleanFilterExpression, validate_expression


class TabularFilter(BaseModel):
    model_config = ConfigDict(extra="forbid")

    column_id: str
    operator: Literal[
        "equals", "not_equals", "contains", "is_blank", "not_blank",
        "greater_than", "greater_than_or_equal", "less_than", "less_than_or_equal",
    ]
    value: str | int | float | bool | None = None
    value_unit: Literal["raw", "percent"] = "raw"


class TabularAggregateCondition(BaseModel):
    """A predicate on a fully computed group, distinct from source-row filters."""
    model_config = ConfigDict(extra="forbid")

    column_id: str | None = None
    target: Literal["aggregate", "share"] = "aggregate"
    operator: Literal["equals", "not_equals", "greater_than", "greater_than_or_equal",
                      "less_than", "less_than_or_equal"]
    value: int | float
    value_unit: Literal["raw", "percent"] = "raw"

    @field_validator("value", mode="before")
    @classmethod
    def finite_threshold(cls, value):
        try:
            valid = not isinstance(value, bool) and isinstance(value, (int, float)) and math.isfinite(value)
        except OverflowError:
            valid = False
        if not valid:
            raise ValueError("Aggregate thresholds must be finite numbers")
        return value


class TabularQueryPlan(BaseModel):
    model_config = ConfigDict(extra="forbid")

    operation: Literal["frequencies", "numeric_summary", "row_count", "distinct_count", "lookup", "row_list"]
    table_id: str
    column_scope: Literal["selected", "all_attributes"] = "selected"
    column_ids: list[str] = Field(default_factory=list, max_length=24)
    group_by: list[str] = Field(default_factory=list, max_length=3)
    identity_column_ids: list[str] = Field(default_factory=list, max_length=24)
    filters: list[TabularFilter] = Field(default_factory=list, max_length=8)
    filter_expression: BooleanFilterExpression | None = None
    having: list[TabularAggregateCondition] = Field(default_factory=list, max_length=4)
    share_of_total: bool = False
    per_group_limit: int | None = Field(default=None, ge=1, le=100)
    order_by: str | None = None
    descending: bool = True
    limit: int | None = Field(default=None, ge=1, le=100)
    statistic: Literal["all", "sum", "average", "min", "max"] = "all"

    @model_validator(mode="after")
    def boolean_shape(self):
        validate_expression(self.filter_expression, len(self.filters))
        return self
