"""A rule that reads another column of the same row: '재고가 안전재고보다 적은 상품은 재고를 안전재고 수량으로'.

The rows are those where one column compares to another on that row, and a value to set may be the other
column's value on that row. Both come from the source cells; a row the comparison cannot decide (a blank or
text where a number is compared) stops the rule, and the copied column must be named in the request.
"""
from app.agent.query.tabular_filters import same_value
from app.agent.writeback.target_semantics import _label_matches

ORDER = {"greater_than": lambda a, b: a > b, "greater_than_or_equal": lambda a, b: a >= b,
         "less_than": lambda a, b: a < b, "less_than_or_equal": lambda a, b: a <= b}
SIGNS = {"equals": "=", "not_equals": "≠", "greater_than": ">", "greater_than_or_equal": "≥",
         "less_than": "<", "less_than_or_equal": "≤"}


def other_columns(rule, table, resolve):
    """(column comparisons, column to copy) with source column ids; a name not found is None."""
    comparisons = [item.model_copy(update={name: resolve(getattr(item, name), table)
                                           for name in ("column_id", "other_column_id")}) for item in rule.column_filters]
    return comparisons, resolve(rule.value_column_id, table) if rule.value_column_id else None


def compared_rows(rows, comparisons):
    """Rows where every column comparison holds, or None when one row cannot be compared."""
    for item in comparisons:
        kept = []
        for row in rows:
            left, right = row.values.get(item.column_id), row.values.get(item.other_column_id)
            if item.operator in ORDER:
                if not (_number(left) and _number(right)):
                    return None
                holds = ORDER[item.operator](left, right)
            else:
                holds = same_value(left, right) == (item.operator == "equals")
            if holds:
                kept.append(row)
        rows = kept
    return rows


def copied_value(cell, header, instruction):
    """(value, reason it is not copied) for the source cell a target takes its value from."""
    if not _label_matches(header, instruction):
        return None, f"가져올 열 ‘{header}’이 요청에 적혀 있지 않습니다."
    if cell is None or cell.value in (None, "") or not isinstance(cell.value, (str, int, float, bool)):
        return None, f"{cell.sheet_name + '!' + cell.address if cell else header}: 가져올 ‘{header}’ 값이 비어 있습니다."
    return cell.value, None


def comparison_text(item, columns):
    return f"‘{columns[item.column_id].display_header}’ {SIGNS[item.operator]} ‘{columns[item.other_column_id].display_header}’"


def _number(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool)
