"""Periods heading pairs of columns ('2017-11' over 'Variation | Cost'): each period read from its amount.

A report may write each month over two or three columns, the amount beside its change from the month
before. The periods then stand one or two columns apart, and the row under them names what each column
holds. The amount ('Cost', '매출') is the column the series is read from; a rate beside it ('Variation',
'증감률', '%') is that amount's change and is never read as the month's value.
"""
import re

MANY = 20  # item rows enough to be a list of like things (usage types, stores), not a statement's lines
_TOTAL = re.compile(r"합계|총계|소계|전체|\b(?:total|sum|all)\b|^계$", re.I)
_NOT_ADDED = re.compile(r"%|\bper\b|price|rate|average|mean|ratio|단가|평균|율|률|비율|당", re.I)
_RATE = re.compile(r"variation|change|growth|rate|ratio|share|%|증감|변동|비율|비중|대비|률|율", re.I)


def amount_columns(dated, below):
    """``dated``: [(column, period cell, period)] of one header row; ``below``: the row under it by column.

    (the same periods, each moved onto its amount column, and the widest step between them) when the row below
    names a repeated measure under every period; else (``dated``, 1)."""
    if len(dated) < 2 or not below:
        return dated, 1
    columns = [column for column, _, _ in dated]
    ends = [*columns[1:], columns[-1] + max(b - a for a, b in zip(columns, columns[1:]))]
    spans = [[column for column in range(start, end) if _name(below, column)] for start, end in zip(columns, ends)]
    if all(len(span) <= 1 for span in spans):
        return dated, 1  # one column a period: nothing to choose
    names = [_name(below, column) for span in spans for column in span]
    measures = [name for name in dict.fromkeys(names) if not _RATE.search(name)]
    chosen = max(measures, key=names.count, default=None)
    if chosen is None or names.count(chosen) < len(dated) - 1:
        return dated, 1
    moved = [(next((column for column in span if _name(below, column) == chosen), None), cell, date)
             for span, (_, cell, date) in zip(spans, dated)]
    moved = [point for point in moved if point[0] is not None]
    return moved, max((b[0] - a[0] for a, b in zip(moved, moved[1:])), default=1)


def _name(row, column):
    value = row.get(column, {}).get("value")
    return " ".join(value.split()).casefold() if isinstance(value, str) and value.strip() else ""


def total_series(rows, start, end, axis, found):
    """The items' sum each period, when the items are many and the table writes no total row of its own.

    '전체 합계' over 315 usage types' monthly cost is what a reader of the table asks first; it is read from
    every item row under the axis, never from the few rows ``found`` as series."""
    if len(found) < 3 or not all(item.get("label_cell") for item in found) or any(
            _NOT_ADDED.search(f"{item.get('basis') or ''} {item.get('declared_unit') or ''} "
                              f"{item['observations'][0].get('number_format') or ''}") for item in found):
        return None  # rates, prices and averages are never added up
    label_column = re.match(r"[A-Z]+", found[0]["label_cell"]).group(0)
    names = {number: cell["value"] for number in sorted(rows) if start < number < end for cell in rows[number].values()
             if re.match(r"[A-Z]+", cell["cell"]).group(0) == label_column and isinstance(cell["value"], str)}
    lines = list(names)
    if len(lines) < MANY or any(_TOTAL.search(name) for name in names.values()):
        return None  # a few lines may be a statement's steps, and a total row of its own is the total
    heads = [cell["value"] for number in range(start - 2, start + 2) for cell in rows.get(number, {}).values()
             if isinstance(cell["value"], str)]
    if not any(re.search(r"합계|총계|\btotal\b", head, re.I) for head in heads):
        return None  # only a table that totals each line ('Total' beside the months) adds its lines up
    from app.services.insights.facts.horizontal_context import period_label
    sums, formats = [], {item["observations"][0].get("number_format") for item in found}
    for column, date_cell, date in axis:
        values = [rows[number][column]["value"] for number in lines if column in rows[number]]
        if any(not isinstance(value, (int, float)) or isinstance(value, bool) for value in values) or not values:
            return None  # a text among the amounts: no sum to state
        letter = re.match(r"[A-Z]+", rows[lines[0]].get(column, {"cell": date_cell["cell"]})["cell"]).group(0)
        sums.append({"period": date.isoformat(), "period_cell": date_cell["cell"],
                     "period_label": period_label(date_cell["value"]),
                     "value": round(sum(values), 6), "value_cell": f"{letter}{lines[0]}:{letter}{lines[-1]}",
                     "number_format": next(iter(formats)) if len(formats) == 1 else None})
    return {**found[0], "metric": "Total", "scope": None, "scope_cell": None, "row": lines[0] - 1,
            "label_cell": f"{label_column}{lines[0]}:{label_column}{lines[-1]}", "label_cells": [],
            "points": [sums[0], sums[-1]], "observations": sums}
