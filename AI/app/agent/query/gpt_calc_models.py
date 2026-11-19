"""The calculation GPT chooses for a question no handler answered.

GPT only names the calculation (which table, columns, filters, grouping, or which cells to combine);
code runs it over the source values, so every number shown comes from the workbook.
"""
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class CalcFilter(BaseModel):
    model_config = ConfigDict(extra="forbid")
    column: str = Field(description="A column name exactly as listed")
    op: Literal["eq", "ne", "gt", "ge", "lt", "le", "contains", "year", "month"] = Field(
        description="year: the date's year equals value (2022); month: its year-month equals value (2022-12)")
    value: str


class TableCalc(BaseModel):
    model_config = ConfigDict(extra="forbid")
    table: int = Field(description="The listed table id")
    filters: list[CalcFilter] = Field(max_length=6)
    group_by: list[str] = Field(max_length=2, description="Column names; empty for one value over the filtered rows")
    period: Literal["none", "year", "month"] = Field(
        description="year/month: a date column in group_by is grouped by its year or year-month")
    measure: str | None = Field(description="The column aggregated; null counts rows")
    aggregate: Literal["sum", "mean", "count", "count_distinct", "min", "max"]
    order: Literal["none", "desc", "asc"]
    pick: Literal["all", "nth", "top", "above_mean", "below_mean"] = Field(
        description="nth: the n-th group in order; top: the first n; above_mean/below_mean: groups beside the groups' mean")
    n: int = Field(ge=0, le=50)
    share: bool = Field(description="Also state each group's share of all groups' total")


class CellItem(BaseModel):
    model_config = ConfigDict(extra="forbid")
    label: str
    expression: str = Field(description="Arithmetic over cell references written as [Sheet!B5], with + - * / ( )")


class CellCalc(BaseModel):
    model_config = ConfigDict(extra="forbid")
    items: list[CellItem] = Field(max_length=40)
    keep: Literal["all", "positive", "negative", "max", "min"] = Field(
        description="Which computed items answer the question")


class CalcPlan(BaseModel):
    model_config = ConfigDict(extra="forbid")
    kind: Literal["table", "cells", "none"]
    method: str = Field(description="One short Korean sentence stating the calculation, naming columns as listed")
    table: TableCalc | None
    cells: CellCalc | None
