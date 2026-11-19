"""Run a GPT-chosen table calculation over every row of one complete source table."""
import re
from dataclasses import dataclass
from datetime import date, datetime
from statistics import mean

from app.agent.query.gpt_calc_planner import column_name
from app.agent.query.tabular_subtotal_rows import _TOTAL


@dataclass(frozen=True)
class TableResult:
    groups: list  # [(label, value, share or None)] in the order shown
    mean: float | None  # the groups' mean, when the pick compares with it
    rows: int  # source rows used
    columns: list  # the columns read
    total: float | None  # all groups' total, when shares are stated
    grouped: tuple = ()  # the names of the columns grouped by


def _number(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def _date_part(value, period):
    if isinstance(value, (datetime, date)):
        text = value.isoformat()
    elif isinstance(value, str) and re.match(r"\d{4}-\d{2}", value):
        text = value
    else:
        return None
    return text[:4] if period == "year" else text[:7]


def _matches(value, item):
    op, wanted = item.op, item.value.strip()
    if op in {"year", "month"}:
        return _date_part(value, op) == wanted
    if op in {"gt", "ge", "lt", "le"}:
        try:
            limit = float(wanted.replace(",", ""))
        except ValueError:
            return False
        return _number(value) and {"gt": value > limit, "ge": value >= limit,
                                   "lt": value < limit, "le": value <= limit}[op]
    text = " ".join(str(value if value is not None else "").split()).casefold()
    if op == "contains":
        return wanted.casefold() in text
    same = text == wanted.casefold() or _number(value) and _same_number(value, wanted)
    return same if op == "eq" else not same


def _same_number(value, wanted):
    try:
        return abs(float(wanted.replace(",", "")) - value) < 1e-9
    except ValueError:
        return False


def run_table(table, calc):
    """TableResult, or None when a named column is not the table's or no row is left."""
    named = {column_name(column).casefold(): column for column in table.columns}
    named.update({column.id.casefold(): column for column in table.columns})
    find = lambda name: named.get(" ".join(str(name).split()).casefold())
    filters = [(find(item.column), item) for item in calc.filters]
    groups = [find(name) for name in calc.group_by]
    measure = find(calc.measure) if calc.measure else None
    if any(column is None for column, _ in filters) or None in groups or calc.measure and measure is None:
        return None
    if measure is None and calc.aggregate not in {"count"}:
        return None
    rows = [row for row in table.rows if not any(isinstance(value, str) and _TOTAL.search(value.strip())
                                                 for value in row.values.values())]
    rows = [row for row in rows if all(_matches(row.values.get(column.id), item) for column, item in filters)]
    buckets = {}
    for row in rows:
        key = tuple(_date_part(row.values.get(column.id), calc.period) if calc.period != "none"
                    and _date_part(row.values.get(column.id), calc.period) else
                    " ".join(str(row.values.get(column.id) if row.values.get(column.id) is not None else "빈칸").split())
                    for column in groups)
        buckets.setdefault(key, []).append(row)
    values = {}
    for key, members in buckets.items():
        if measure is None:
            values[key] = len(members)
            continue
        cells = [row.values.get(measure.id) for row in members]
        if calc.aggregate == "count_distinct":
            values[key] = len({" ".join(str(value).split()) for value in cells if value not in (None, "")})
        elif calc.aggregate == "count":
            values[key] = sum(1 for value in cells if value not in (None, ""))
        else:
            numbers = [value for value in cells if _number(value)]
            if not numbers:
                continue
            values[key] = {"sum": sum, "mean": mean, "min": min, "max": max}[calc.aggregate](numbers)
    if not values:
        return None
    items = list(values.items())
    if calc.order != "none":
        items.sort(key=lambda item: item[1], reverse=calc.order == "desc")
    middle = mean(value for _, value in items) if calc.pick in {"above_mean", "below_mean"} else None
    if calc.pick == "nth":
        items = items[calc.n - 1:calc.n] if calc.n >= 1 else []
    elif calc.pick == "top":
        items = items[:max(calc.n, 1)]
    elif middle is not None:
        items = [item for item in items if (item[1] > middle if calc.pick == "above_mean" else item[1] < middle)]
    total = sum(values.values()) if calc.share else None
    shown = [(" · ".join(key) or "전체", value, value / total * 100 if total else None) for key, value in items]
    used = [column for column, _ in filters] + groups + ([measure] if measure else [])
    return TableResult(shown, middle, len(rows), list(dict.fromkeys(used)), total,
                       tuple(column_name(column) for column in groups))
