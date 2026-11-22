"""Columns compared with each other, values gathered into named sets, and more figures of the same rows.

- "2025년 제품별 판매량 중 가장 적은 제품": the products are columns, so each column's total is compared.
- "북동부 인구 추이": one row's values across its year columns, in order.
- "평일과 주말 중 평균 매출이 높은 쪽": 월~금 and 토·일 are gathered into two named groups.
- "초과한 프로젝트 몇 개고, 초과 금액은 얼마야": the count, and the sum asked of the same rows.
"""
from statistics import mean, median

from app.agent.query.gpt_calc_filters import _number
from app.agent.query.gpt_calc_picks import picked, then_value
from app.agent.query.gpt_calc_planner import column_name
from app.agent.query.gpt_calc_result import TableResult

_AGGREGATE = {"sum": sum, "mean": mean, "median": median, "min": min, "max": max, "count": len}


def across_result(calc, columns, rows, used, skipped):
    """Each listed column's figure over the rows kept, compared like groups; None when a column is not the table's."""
    if not columns or None in columns or not rows:
        return None
    values = {}
    for column in columns:
        numbers = [value for row in rows if _number(value := row.values.get(column.id))]
        if numbers:
            values[(column_name(column),)] = _AGGREGATE.get(calc.aggregate, sum)(numbers)
    if not values:
        return None
    items, middle = picked(calc.model_copy(update={"period": "none"}), values)  # columns in their listed order
    total = sum(values.values()) if calc.share else None
    shown = [(key[0], value, value / total * 100 if total else None) for key, value in items]
    return TableResult(shown, middle, len(rows), list(dict.fromkeys([*used, *columns])), total, ("항목",),
                       skipped=skipped, then=then_value(calc, items))


def binned(calc, label):
    """The named set a group value belongs to (월 → 평일), the value itself without sets, None outside every set."""
    if not calc.bins:
        return label
    folded = " ".join(str(label).split()).casefold()
    return next((item.name for item in calc.bins
                 if folded in {" ".join(str(value).split()).casefold() for value in item.values}), None)


def extras(calc, rows, find, formula_of):
    """(label, value) of the further figures asked of the same rows: 초과 금액 합계 beside the count."""
    found = []
    for item in calc.also:
        if item.row_formula:
            formula = formula_of(item.row_formula)
            cells = [formula[1](row) for row in rows] if formula else []
        else:
            column = find(item.measure) if item.measure else None
            cells = [row.values.get(column.id) for row in rows] if column else [1] * len(rows)
        numbers = [value for value in cells if _number(value)]
        if numbers or item.aggregate == "count":
            found.append((item.label, _AGGREGATE.get(item.aggregate, sum)(numbers) if numbers else 0))
    return tuple(found)
