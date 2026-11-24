"""Run a GPT-chosen table calculation over every row of one complete source table."""
import re
from statistics import mean, median

from app.agent.query.gpt_calc_filters import _ALTERNATIVE, _date_part, _matches, _number
from app.agent.query.gpt_calc_picks import changes, column_totals, holders, named_periods, picked, then_value
from app.agent.query.gpt_calc_bounds import _with_mean
from app.agent.query.gpt_calc_across import _AGGREGATE, across_result, binned, extras
from app.agent.query.gpt_calc_planner import column_name
from app.agent.query.gpt_calc_result import TableResult
from app.agent.query.gpt_calc_values import _label, _minus, _row_name, as_day, row_formula, with_date_group
from app.agent.query.tabular_subtotal_rows import _TOTAL


def run_table(table, calc, headings=None):
    """TableResult, or None when a named column is not the table's or no row is left."""
    named = {**{column_name(column).casefold(): column for column in table.columns},
             **{column.id.casefold(): column for column in table.columns}}
    find = lambda name: named.get(" ".join(str(name).split()).casefold())  # noqa: E731
    filters = [(find(item.column), item, find(item.value) if item.op.endswith("_column") else None)
               for item in calc.filters if item.value.strip() != "*" and item.op != "under"]  # "*": no condition
    under = {" ".join(item.value.split()).casefold() for item in calc.filters if item.op == "under"}
    filters = [(column, _with_mean(table, column, item), other) for column, item, other in filters]  # 평균 이상
    groups = with_date_group(table, [find(name) for name in calc.group_by], calc.period)  # 매장 + 날짜 for 월별
    formula = row_formula(table, calc.row_formula) if calc.row_formula else None  # Qty × UnitPrice × (1 - Discount)
    if calc.row_formula and formula is None:
        return None
    measure = formula[0][-1] if formula else find(calc.measure) if calc.measure else None
    # A ratio's denominator: one column, or several written "매우만족, 만족, 보통" (all responses).
    denominators = ([find(calc.denominator)] if find(calc.denominator) else [find(part) for part in re.split(
        r"\s*[,+]\s*", calc.denominator)]) if calc.aggregate == "ratio" and calc.denominator else []
    whole = [find(item) for item in calc.add] if formula and calc.aggregate == "ratio" else []
    if whole and None not in whole and set(formula[0]) <= set(whole) and not set(formula[0]) <= set(denominators):
        denominators = whole  # the plan listed the whole in add (불만+매우불만 over all five answers), not in denominator
    denominator = denominators[0] if denominators and None not in denominators else None
    subtract = find(calc.subtract) if calc.subtract and not formula else None  # a row formula says it all
    minus = [find(item) for item in calc.minus] if subtract else []
    added = [find(item) for item in calc.add if find(item) is not measure] if not formula else []
    name = find(calc.name_by) if calc.name_by else None
    if subtract is not None and subtract is measure:  # a column minus itself is 0 for every row
        return None
    if calc.subtract and subtract is None and not formula or None in minus or None in added or added and measure is None or calc.name_by and name is None:
        return None
    if any(column is None or item.op.endswith("_column") and other is None for column, item, other in filters) \
            or None in groups or calc.measure and measure is None and not formula or denominators and denominator is None:
        return None
    # A ratio over no other column ('예' 응답 비율, 부산 창고 비중) is the filtered rows' share of all rows.
    within = calc.aggregate == "ratio" and (denominator is None or denominators == [measure]) and not groups
    if measure is None and calc.aggregate != "count" and not within and not calc.across:
        return None
    asked = {item.value.strip().casefold() for item in calc.filters if item.op in {"eq", "contains"}}  # rows named
    rows = [row for row in table.rows if not any(isinstance(value, str) and _TOTAL.search(value.strip())
                                                 and value.strip().casefold() not in asked for value in row.values.values())]
    skipped = tuple(label for number, label in (headings or {}).items() if label.strip().casefold() not in asked)
    rows = [row for row in rows if (headings or {}).get(row.row_number) not in skipped]
    # A ratio's base: the rows its scope filters keep (강남점 days for "강남점 매출이 200만원 이상인 날의 비율").
    every = [row for row in rows if all(_matches(row.values.get(column.id), item, row, other)
                                        for column, item, other in filters if item.scope)]
    # Conditions on one column alike ("month 07", "month 08", "month 09") are alternatives: 3분기.
    alike = {}
    for column, item, other in filters:
        alike.setdefault((column.id, item.op) if item.op in _ALTERNATIVE else id(item), []).append((column, item, other))
    rows = [row for row in rows if all(any(_matches(row.values.get(column.id), item, row, other)
                                           for column, item, other in group) for group in alike.values())]
    if under:  # the rows of one section: "Year 2026" over its months
        marks = sorted((number, " ".join(label.split()).casefold()) for number, label in (headings or {}).items())
        section = lambda number: next((label for mark, label in reversed(marks) if mark < number), None)  # noqa: E731
        rows = [row for row in rows if section(row.row_number) in under]
    if calc.across:  # columns compared with each other (제품별 열), or one row across its year columns
        return across_result(calc, [find(item) for item in calc.across], rows, [column for column, _, _ in filters], skipped)
    if within:
        amount = (lambda chosen: len(chosen)) if measure is None else (
            lambda chosen: sum(row.values.get(measure.id) for row in chosen if _number(row.values.get(measure.id))))
        part, whole = amount(rows), amount(every)
        if not whole:
            return None
        used = [column for column, _, _ in filters] + ([measure] if measure else [])
        return TableResult([("전체", part / whole * 100, None)], None, len(every), list(dict.fromkeys(used)), None,
                           parts=(part, whole), skipped=skipped)
    if calc.rank_of and len(groups) == 1 and len({_label(row.values.get(groups[0].id)) for row in rows}) >= 0.9 * len(rows):
        groups = []  # "선풍기는 몇 위" among names nearly all distinct: each row is ranked, a repeated name not summed
    ranked = (calc.pick in {"top", "nth", "above_mean", "below_mean"} or calc.rank_of) and not groups  # rows ranked
    buckets, period_position = {}, None
    for row in rows:
        key = [] if groups or not ranked else [_row_name(table, row, measure), str(row.row_number)]
        for position, column in enumerate(groups):
            part = _date_part(row.values.get(column.id), calc.period) if calc.period != "none" else None
            period_position = position if part else period_position
            label = part or _label(row.values.get(column.id))
            key.append(binned(calc, label) if position == 0 else label)  # 월~금 → 평일
        if None not in key:
            buckets.setdefault(tuple(key), []).append(row)
    if calc.aggregate == "mean" and calc.then == "sum" and all(len(rows) == 1 for rows in buckets.values()):
        calc = calc.model_copy(update={"then": "mean"})  # one row a group: the mean asked is of the groups picked
    values, derived, dated = {}, {}, False
    for key, members in buckets.items():
        if measure is None:
            values[key] = len(members)
            continue
        cells = [formula[1](row) if formula else row.values.get(measure.id) for row in members]
        if added:  # each row's total over its columns: Q1+Q2+Q3+Q4
            cells = [value + sum(row.values.get(column.id) for column in added) if _number(value) and all(
                _number(row.values.get(column.id)) for column in added) else None for value, row in zip(cells, members)]
        if subtract is not None:  # each row's change (2026 minus 2025), or days between two dates
            for column in [subtract, *minus]:
                cells = [_minus(value, row.values.get(column.id)) for value, row in zip(cells, members)]
        if calc.absolute:  # "차이가 가장 큰": the size of the difference, whichever way
            cells = [abs(value) if _number(value) else value for value in cells]
        derived[key] = list(zip(members, cells))
        if calc.aggregate == "count_distinct":
            values[key] = len({" ".join(str(value).split()) for value in cells if value not in (None, "")})
        elif calc.aggregate == "count":
            values[key] = sum(1 for value in cells if value not in (None, ""))
        elif calc.aggregate == "ratio" and denominator is not None:
            pairs = [(part, sum(row.values.get(column.id) for column in denominators)
                      if all(_number(row.values.get(column.id)) for column in denominators) else None)
                     for part, row in zip(cells, members)]
            pairs = [(part, whole) for part, whole in pairs if _number(part) and _number(whole)]
            if pairs and sum(whole for _, whole in pairs):
                values[key] = sum(part for part, _ in pairs) / sum(whole for _, whole in pairs) * 100
        else:
            numbers = [value for value in cells if _number(value)]
            days = [day.toordinal() for value in cells if (day := as_day(value))] if calc.aggregate in {"max", "min"} else []
            dated, numbers = (True, days) if days and not numbers else (dated, numbers)  # 가장 최근 주문 날짜
            if not numbers:
                continue
            values[key] = {**_AGGREGATE, "count": len}[calc.aggregate](numbers)
    values = values or ({(): 0} if not groups and calc.aggregate in {"count", "count_distinct"} else {})  # none left: 0
    if not values or (period := named_periods(calc, len(groups), values, period_position))[1] is None \
            and calc.versus_previous != "none":
        return None  # 전월 대비 with no date grouped, nor a column naming periods ('FY20' · 'FY21'), compares nothing
    values, period_position = period
    # Months named without a year (January, Sept) are no periods code can order: they stay in the source's order.
    items, middle, place = picked(calc if period_position is not None else calc.model_copy(update={"period": "none"}),
                                  values, period_position)
    total = sum(values.values()) if calc.share else None
    shown = []
    for key, value in items:
        label, names = " · ".join(key[:1] if ranked else key) or "전체", holders(calc, key, value, derived, name)
        label = names if names and (label == "전체" or ranked) else f"{label} ({names})" if names and names != label else label
        shown.append((label, value, value / total * 100 if total else None))
    used = [column for column, _, _ in filters] + [other for _, _, other in filters if other] + groups + (
        denominators if denominator else []) + (formula[0] if formula else []) + ([subtract] if subtract else []) + added + ([name] if name else []) + (
        [measure] if measure else [])
    used = [column for column in dict.fromkeys(used) if column is not measure] + ([measure] if measure else [])
    return TableResult(shown, middle, len(rows), used, total,
                       tuple(column_name(column) for column in groups), skipped=skipped,
                       by_column=column_totals(calc, items, buckets, measure, added if not subtract else [], column_name),
                       then=then_value(calc, items), changes=changes(calc, values, period_position),
                       dated=dated, place=place, extras=extras(calc, rows, find, lambda text: row_formula(table, text)), sizes={" · ".join(key) or "전체": len(buckets[key]) for key, _ in items} if calc.share else {})
