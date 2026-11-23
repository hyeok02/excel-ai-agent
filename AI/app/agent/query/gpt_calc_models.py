"""The calculation GPT chooses for a question no handler answered.

GPT only names the calculation (which table, columns, filters, grouping, or which cells to combine);
code runs it over the source values, so every number shown comes from the workbook.
"""
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class CalcFilter(BaseModel):
    model_config = ConfigDict(extra="forbid")
    column: str = Field(description="A column name exactly as listed")
    op: Literal["eq", "ne", "gt", "ge", "lt", "le", "contains", "year", "month", "quarter", "under", "in", "not_in",
                "gt_column", "ge_column", "lt_column", "le_column"] = Field(
        description="year: the date's year equals value (2022); month: its year-month equals value (2022-12); quarter: 2022-Q3; "
                    "gt/ge/lt/le on a date column compare with a year, year-month or date; "
                    "이후/이전 include the named period (2020년 이후: ge 2020), 초과/미만 exclude it; "
                    "under: the rows below the group_rows heading named in value (one section's rows); "
                    "in/not_in: the value is among a comma-separated list, or another table's column written as a range "
                    "[Sheet!C2:C152]; "
                    "gt/ge/lt/le with value mean compare with the column's mean; "
                    "several filters on one column are alternatives; "
                    "*_column: compares with the same row's value of the column named in value")
    value: str
    scope: bool = Field(default=False, description="For a ratio without group_by: true when this filter limits the rows "
                        "the share is taken of (one member's rows), false when it picks the part (rows above a level)")


class Having(BaseModel):
    model_config = ConfigDict(extra="forbid")
    op: Literal["gt", "ge", "lt", "le", "eq", "ne"]
    value: float


class Bin(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: str = Field(description="The set's name as asked")
    values: list[str] = Field(max_length=60, description="The first group_by column's values gathered in it")


class Extra(BaseModel):
    model_config = ConfigDict(extra="forbid")
    label: str = Field(description="What the figure is, in Korean")
    measure: str | None = Field(default=None, description="The column aggregated; null with count")
    row_formula: str | None = Field(default=None, description="Or arithmetic over each row's columns by letter")
    aggregate: Literal["sum", "mean", "median", "count", "min", "max"] = "sum"


class TableCalc(BaseModel):
    model_config = ConfigDict(extra="forbid")
    table: int = Field(description="The listed table id")
    filters: list[CalcFilter] = Field(max_length=12)
    group_by: list[str] = Field(max_length=2, description="Column names; empty for one value over the filtered rows")
    period: Literal["none", "year", "half", "quarter", "month", "weekday"] = Field(
        description="year/half/quarter/month/weekday: a date column in group_by is grouped by its year, half "
                    "(2025-H1), quarter, year-month or day of the week")
    measure: str | None = Field(description="The column aggregated; null counts rows")
    row_formula: str | None = Field(default=None, description="Instead of measure, arithmetic over each row's columns "
                                    "written by letter, e.g. [G]*[H]*(1-[I]) for quantity × price after discount, [E]-[D] for days between "
                                    "two dates; + - * / ( ) and abs() only, no spreadsheet functions; else null")
    aggregate: Literal["sum", "mean", "median", "count", "count_distinct", "min", "max", "range", "ratio"] = Field(
        description="ratio: sum of measure / sum of denominator × 100 (a rate such as spent over budget)")
    denominator: str | None = Field(description="The column divided by, for ratio; else null")
    add: list[str] = Field(max_length=24, description="Columns added to measure in each row before aggregating "
                                                     "(Q1..Q4 or months laid out as columns, for a yearly total); else []")
    subtract: str | None = Field(description="A column subtracted from measure in each row before aggregating "
                                             "(this year's column minus last year's for a change); else null")
    minus: list[str] = Field(default_factory=list, max_length=12, description="More columns subtracted with "
                             "subtract (two columns minus two others)")
    absolute: bool = Field(default=False, description="Use the size of measure minus subtract whatever its sign "
                           "(the largest gap between two scores)")
    name_by: str | None = Field(default=None, description="With max or min per group: the column naming the row "
                                "that holds it (the student with each class's top score); else null")
    then: Literal["none", "sum", "mean"] = Field(default="none", description="What the question asks of the groups "
                                                 "shown together: mean for a monthly average of monthly totals, or for "
                                                 "the mean of the top 3 days")
    change: bool = Field(default=False, description="With group_by a category and a date column and a period: each "
                         "category's change from its first to its last period, with the rate (which store grew more)")
    across: list[str] = Field(default_factory=list, max_length=40, description="Columns compared with each other "
                              "(products or years laid out as columns): each column's aggregate over the rows kept is "
                              "one group, ordered and picked like groups; group_by empty")
    bins: list[Bin] = Field(default_factory=list, max_length=12, description="Named sets of the first group_by "
                            "column's values, each one group (some values against the others); rows in no set are left out")
    also: list[Extra] = Field(default_factory=list, max_length=4, description="More figures asked of the same filtered "
                              "rows, without group_by (the excess amount beside the count of projects over budget)")
    versus_previous: Literal["none", "difference", "rate"] = Field(default="none", description="Each period group "
                                                                   "against the one before it: 전월 대비 증가율 is rate, 전월보다 늘어난 양 difference")
    having: Having | None = Field(default=None, description="Keep only the groups whose value meets this (members "
                                  "appearing N times or more: count per member, ge N); their number is stated")
    rank_of: str | None = Field(default=None, description="The group whose place in the order is asked")
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
    keep: Literal["all", "positive", "negative", "max", "min", "above", "below"] = Field(
        description="Which computed items answer the question; above/below: those beyond threshold")
    threshold: float | None = Field(default=None, description="For keep above/below: the value compared with "
                                    "(60 for a share over 60%); else null")


class CalcPlan(BaseModel):
    model_config = ConfigDict(extra="forbid")
    kind: Literal["table", "cells", "none"]
    method: str = Field(description="One short Korean sentence stating the calculation, naming columns as listed")
    table: TableCalc | None
    cells: CellCalc | None
