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
    parts: tuple = ()  # (part, whole) of a share of the filtered rows in all rows
    skipped: tuple = ()  # heading rows left out (regions over their states)


_number = lambda value: isinstance(value, (int, float)) and not isinstance(value, bool)  # noqa: E731


def _date_part(value, period):
    if isinstance(value, (datetime, date)):
        text = value.isoformat()
    elif isinstance(value, str) and re.match(r"\d{4}-\d{2}", value):
        text = value
    else:
        return None
    return text[:4] if period == "year" else text[:7]


def _matches(value, item, row=None, other=None):
    op, wanted = item.op, item.value.strip()
    if op.endswith("_column"):  # 재고수량 < 안전재고: two values of one row
        compared = row.values.get(other.id) if row is not None and other is not None else None
        return _number(value) and _number(compared) and {"gt_column": value > compared, "ge_column": value >= compared,
                                                         "lt_column": value < compared, "le_column": value <= compared}[op]
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


def run_table(table, calc, headings=None):
    """TableResult, or None when a named column is not the table's or no row is left."""
    named = {**{column_name(column).casefold(): column for column in table.columns},
             **{column.id.casefold(): column for column in table.columns}}
    find = lambda name: named.get(" ".join(str(name).split()).casefold())  # noqa: E731
    filters = [(find(item.column), item, find(item.value) if item.op.endswith("_column") else None)
               for item in calc.filters]
    groups = [find(name) for name in calc.group_by]
    measure = find(calc.measure) if calc.measure else None
    denominator = find(calc.denominator) if calc.aggregate == "ratio" and calc.denominator else None
    subtract = find(calc.subtract) if calc.subtract else None
    if calc.subtract and subtract is None:
        return None
    if any(column is None or item.op.endswith("_column") and other is None for column, item, other in filters) \
            or None in groups or calc.measure and measure is None or calc.denominator and denominator is None:
        return None
    # A ratio over no other column ('예' 응답 비율, 부산 창고 비중) is the filtered rows' share of all rows.
    within = calc.aggregate == "ratio" and (denominator is None or denominator is measure) and not groups
    if measure is None and calc.aggregate != "count" and not within:
        return None
    asked = {item.value.strip().casefold() for item in calc.filters if item.op in {"eq", "contains"}}  # rows named
    rows = [row for row in table.rows if not any(isinstance(value, str) and _TOTAL.search(value.strip())
                                                 and value.strip().casefold() not in asked for value in row.values.values())]
    skipped = tuple(label for number, label in (headings or {}).items() if label.strip().casefold() not in asked)
    rows = [row for row in rows if (headings or {}).get(row.row_number) not in skipped]
    every = rows
    rows = [row for row in rows if all(_matches(row.values.get(column.id), item, row, other)
                                       for column, item, other in filters)]
    if within:
        amount = (lambda chosen: len(chosen)) if measure is None else (
            lambda chosen: sum(row.values.get(measure.id) for row in chosen if _number(row.values.get(measure.id))))
        part, whole = amount(rows), amount(every)
        if not whole:
            return None
        used = [column for column, _, _ in filters] + ([measure] if measure else [])
        return TableResult([("전체", part / whole * 100, None)], None, len(every), list(dict.fromkeys(used)), None,
                           parts=(part, whole), skipped=skipped)
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
        if subtract is not None:  # each row's change: 2026 minus 2025 of the same row
            cells = [value - row.values.get(subtract.id) if _number(value) and _number(row.values.get(subtract.id))
                     else None for value, row in zip(cells, members)]
        if calc.aggregate == "count_distinct":
            values[key] = len({" ".join(str(value).split()) for value in cells if value not in (None, "")})
        elif calc.aggregate == "count":
            values[key] = sum(1 for value in cells if value not in (None, ""))
        elif calc.aggregate == "ratio" and denominator is not None:
            pairs = [(row.values.get(measure.id), row.values.get(denominator.id)) for row in members]
            pairs = [(part, whole) for part, whole in pairs if _number(part) and _number(whole)]
            if pairs and sum(whole for _, whole in pairs):
                values[key] = sum(part for part, _ in pairs) / sum(whole for _, whole in pairs) * 100
        else:
            numbers = [value for value in cells if _number(value)]
            if not numbers:
                continue
            values[key] = {"sum": sum, "mean": mean, "min": min, "max": max}[calc.aggregate](numbers)
    if not values:
        return None
    items = sorted(values.items()) if calc.period != "none" else list(values.items())  # months in order
    if calc.order != "none" and not (calc.period != "none" and calc.pick == "all"):
        items.sort(key=lambda item: item[1], reverse=calc.order == "desc")
    middle = mean(value for _, value in items) if calc.pick in {"above_mean", "below_mean"} else None
    if calc.pick in {"nth", "top"}:  # a group tied with the last one picked is picked too
        n = max(calc.n, 1)
        last = items[n - 1][1] if n <= len(items) else None
        items = [] if last is None else [item for number, item in enumerate(items) if item[1] == last and number >= n - 1
                                          or calc.pick == "top" and number < n]
    elif middle is not None:
        items = [item for item in items if (item[1] > middle if calc.pick == "above_mean" else item[1] < middle)]
    total = sum(values.values()) if calc.share else None
    shown = [(" · ".join(key) or "전체", value, value / total * 100 if total else None) for key, value in items]
    used = [column for column, _, _ in filters] + [other for _, _, other in filters if other] + groups + (
        [denominator] if denominator else []) + ([subtract] if subtract else []) + ([measure] if measure else [])
    return TableResult(shown, middle, len(rows), list(dict.fromkeys(used)), total,
                       tuple(column_name(column) for column in groups), skipped=skipped)
