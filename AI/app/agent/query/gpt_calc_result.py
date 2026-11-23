"""What a table calculation found, for the answer to state."""
from dataclasses import dataclass, field


@dataclass(frozen=True)
class TableResult:
    groups: list  # [(label, value, share or None)] in the order shown
    mean: float | None  # the groups' mean, when the pick compares with it
    rows: int  # source rows used
    columns: list  # the columns read
    total: float | None  # all groups' total, when shares are stated
    grouped: tuple = ()  # the names of the columns grouped by
    parts: tuple = ()  # (part, whole) of a share of the filtered rows in all rows
    skipped: tuple = ()  # heading rows left out (regions over their states)
    by_column: tuple = ()  # (column, value) of one group's columns added together: Q1 … Q4, Mid-2011 … Mid-2024
    then: tuple | None = None  # the sum or mean of the groups picked (상위 3일의 평균)
    changes: tuple = ()  # (category, first period, value, last period, value) per category
    sizes: dict = field(default_factory=dict)  # each group's rows, stated with shares
    dated: bool = False  # values are days (date ordinals): the latest order date
    place: tuple | None = None  # (place, of how many, value) of the group rank_of names
    extras: tuple = ()  # (label, value) of more figures asked of the same rows: 초과 금액 합계
