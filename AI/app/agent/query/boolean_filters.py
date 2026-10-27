"""Shared indexed/streamed evaluation; an unknown predicate never becomes false."""
from app.agent.query.boolean_filter_models import validate_expression
from app.agent.query.formula_resolution_values import EXCEL_ERRORS
from openpyxl.styles.numbers import is_date_format

_UNKNOWN = object()


def evaluate_filters(row, filters, columns, expression=None):
    from app.agent.query.tabular_filters import finite_number, matches

    try:
        validate_expression(expression, len(filters))
    except ValueError:
        return None
    negative = negative_predicates(expression)
    values = []
    for index, condition in enumerate(filters):
        if condition.column_id not in columns:
            return None
        value = row.values.get(condition.column_id)
        if row.formulas.get(condition.column_id) and value is None:
            return None
        if isinstance(value, str) and value in EXCEL_ERRORS:
            values.append(_UNKNOWN)
            continue
        if (is_date_format(row.number_formats.get(condition.column_id, "General"))
                and condition.operator not in {"is_blank", "not_blank"}):
            return None  # Calendar/date normalization is not a boolean numeric comparison.
        numeric = isinstance(condition.value, (int, float)) and not isinstance(condition.value, bool)
        blank_test = condition.operator in {"is_blank", "not_blank"} or condition.value in (None, "")
        incompatible = numeric and not finite_number(value) or isinstance(condition.value, bool) and not isinstance(value, bool)
        if (value in (None, "") and isinstance(condition.value, str) and condition.value
                and condition.operator in {"equals", "contains"} and index not in negative):
            values.append(False)  # An actual empty cell does not contain a requested positive text label.
            continue
        if not blank_test and (value in (None, "") or incompatible):
            values.append(_UNKNOWN)
            continue
        result = matches(value, condition, row.number_formats.get(condition.column_id, "General"),
                         columns[condition.column_id].header)
        if result is None:
            return None
        values.append(result)
    result = evaluate_tree(expression, values) if expression is not None else all(values)
    return None if result is _UNKNOWN else result


def negative_predicates(node, negated=False):
    if node is None:
        return set()
    if node.operator == "predicate":
        return {node.filter_index} if negated else set()
    return set().union(*(negative_predicates(child, negated != (node.operator == "not"))
                         for child in node.children))


def evaluate_tree(node, values):
    if node.operator == "predicate":
        return values[node.filter_index]
    children = [evaluate_tree(child, values) for child in node.children]
    if node.operator == "not":
        return _UNKNOWN if children[0] is _UNKNOWN else not children[0]
    deciding = False if node.operator == "and" else True
    if any(value is deciding for value in children):
        return deciding
    if any(value is _UNKNOWN for value in children):
        return _UNKNOWN
    return not deciding


def render_expression(expression, labels):
    if expression is None:
        return " AND ".join(labels)
    if expression.operator == "predicate":
        return labels[expression.filter_index]
    parts = [render_expression(child, labels) for child in expression.children]
    if expression.operator == "not":
        return f"NOT ({parts[0]})"
    return "(" + f" {expression.operator.upper()} ".join(parts) + ")"
