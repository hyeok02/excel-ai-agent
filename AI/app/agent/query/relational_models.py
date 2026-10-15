"""Bounded two-table plans: source IDs and predicates, never model-made values."""
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from app.agent.query.tabular_query_models import TabularFilter


class RelationalKey(BaseModel):
    model_config = ConfigDict(extra="forbid")
    left_column_id: str
    right_column_id: str


class RelationalFilter(TabularFilter):
    side: Literal["left", "right"]


class RelationalQueryPlan(BaseModel):
    model_config = ConfigDict(extra="forbid")
    operation: Literal["lookup", "row_list", "row_count", "numeric_summary"]
    left_table_id: str
    right_table_id: str
    on: list[RelationalKey] = Field(min_length=1, max_length=4)
    join_type: Literal["inner", "left"] = "left"
    population: Literal["all_left", "matched_only"] = "all_left"
    # Qualified references are e.g. left.A and right.F. Excel column IDs alone
    # are ambiguous when the sources occupy different sheets.
    column_ids: list[str] = Field(default_factory=list, max_length=12)
    group_by: list[str] = Field(default_factory=list, max_length=3)
    filters: list[RelationalFilter] = Field(default_factory=list, max_length=8)
    statistic: Literal["sum", "average", "min", "max"] = "sum"


class RelationalError(ValueError):
    """A readable source/coverage failure; callers must not use guessed totals."""
