"""Typed, unit-aware predicates and ordering over a validated table population."""
import math
from decimal import Decimal

from app.agent.query.excel_number_formats import parse_number_format


def same_value(expected, actual):
    if expected in (None, "") and actual in (None, ""):
        return True
    if isinstance(expected, bool) != isinstance(actual, bool):
        return False
    return expected == actual


def filtered_rows(table, filters, expression=None):
    columns = {column.id: column for column in table.columns}
    if expression is not None:
        from app.agent.query.boolean_filters import evaluate_filters
        accepted = [(row, evaluate_filters(row, filters, columns, expression)) for row in table.rows]
        return None if any(value is None for _, value in accepted) else [row for row, value in accepted if value]
    rows = list(table.rows)
    for condition in filters:
        if condition.column_id not in columns:
            return None
        matched = []
        for row in rows:
            result = matches(
                row.values[condition.column_id], condition,
                row.number_formats.get(condition.column_id, "General"),
                columns[condition.column_id].header,
            )
            if result is None:
                return None
            if result:
                matched.append(row)
        rows = matched
    return rows


def matches(value, condition, number_format="General", header=""):
    operator = condition.operator
    if operator == "is_blank":
        return value in (None, "")
    if operator == "not_blank":
        return value not in (None, "")
    if operator == "contains":
        return isinstance(value, str) and isinstance(condition.value, str) and condition.value.casefold() in value.casefold()
    percent = getattr(condition, "value_unit", "raw") == "percent"
    if operator in {"equals", "not_equals"} and not percent:
        equal = (value.casefold() == condition.value.casefold()
                 if isinstance(value, str) and isinstance(condition.value, str)
                 else same_value(value, condition.value))
        return equal if operator == "equals" else not equal
    comparisons = {
        "equals": lambda left, right: left == right,
        "not_equals": lambda left, right: left != right,
        "greater_than": lambda left, right: left > right,
        "greater_than_or_equal": lambda left, right: left >= right,
        "less_than": lambda left, right: left < right,
        "less_than_or_equal": lambda left, right: left <= right,
    }
    if operator not in comparisons:
        return None
    if value in (None, ""):
        return False
    if not finite_number(value) or not finite_number(condition.value):
        return None
    actual, threshold = Decimal(str(value)), Decimal(str(condition.value))
    if percent:
        spec = parse_number_format(number_format)
        if not spec.percent and "%" not in header and "percent" not in header.casefold():
            return None
        actual *= spec.multiplier
    return comparisons[operator](actual, threshold)


def ordered_rows(rows, plan):
    if plan.order_by:
        values = [row.values.get(plan.order_by) for row in rows]
        if any(value in (None, "") for value in values):
            return None
        if all(finite_number(value) for value in values):
            styles = [parse_number_format(row.number_formats.get(plan.order_by, "General")) for row in rows]
            units = {(style.prefix, style.suffix, style.multiplier, style.divisor, style.percent) for style in styles}
            if len(units) > 1:
                return None
            key = lambda row: Decimal(str(row.values[plan.order_by]))
        elif all(isinstance(value, str) for value in values):
            key = lambda row: row.values[plan.order_by].casefold()
        else:
            return None
        rows = sorted(rows, key=key, reverse=plan.descending)
    return rows[:plan.limit] if plan.limit else rows


def finite_number(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)
