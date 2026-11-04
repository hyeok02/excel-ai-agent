"""Turn a model's reading of an edit request into source cells and computed values.

The model reads the request ("쿠키 단가를 10% 올려줘") as one rule: a source table,
the conditions that pick its rows (Category = Cookies), one target column
(UnitPrice) and one operation. It may translate the user's words into source
labels; it does not choose rows or values. Here every name must exist in the
source, the whole table must be read, every matching row is taken, and each new
value is computed from the operation. The reading is shown to the reviewer, and
the stated value or calculation is still checked against the request itself.
A rule that cannot be applied to every matching row is not applied at all.
"""
import re
from datetime import datetime
from decimal import Decimal

from app.agent.query.ambiguity_labels import resolve_unique_column
from app.agent.query.tabular_filters import filtered_rows
from app.agent.query.tabular_validation import validated_table
from app.agent.writeback.derived_values import _clean
from app.agent.writeback.models import WritebackChangeDraft
from app.agent.writeback.references import MAX_CHANGES, key
from app.agent.writeback.value_authorization import as_number
from app.agent.writeback.writeback_tables import writeback_tables

OPERATIONS = {"set": "{amount}(으)로 바꾸는", "clear": "비우는",
              "percent_increase": "{amount}% 올리는", "percent_decrease": "{amount}% 내리는",
              "add": "{amount}만큼 늘리는", "subtract": "{amount}만큼 줄이는", "multiply": "{amount}배로 바꾸는"}
OPERATORS = {"equals": "=", "not_equals": "≠", "contains": "포함", "greater_than": ">",
             "greater_than_or_equal": "≥", "less_than": "<", "less_than_or_equal": "≤",
             "is_blank": "빈칸", "not_blank": "빈칸 아님"}


class RuleRejected(Exception):
    """The reading cannot be applied to every matching source row."""


class RuleNotFound(RuleRejected):
    """The reading names a table or column the source does not have; cell drafts may still apply."""


def rule_drafts(rule, summary, index):
    """(drafts, reading shown to the reviewer) or RuleRejected."""
    tables = [table for table in writeback_tables(summary) if table.id == rule.table_id]
    if len(tables) != 1:
        raise RuleNotFound("해석한 표를 원본에서 찾지 못했습니다.")
    table = tables[0]
    target = resolve_unique_column(rule.target_column_id, table)
    filters = [item.model_copy(update={"column_id": resolve_unique_column(item.column_id, table)})
               for item in rule.filters]
    if target is None or any(item.column_id is None for item in filters):
        raise RuleNotFound("해석한 열 이름을 원본 표에서 하나로 찾지 못했습니다.")
    if not validated_table(table, index, {target, *(item.column_id for item in filters)}):
        raise RuleRejected("표 전체를 원본에서 확인하지 못해 조건에 맞는 모든 행을 바꾼다고 보장할 수 없습니다.")
    rows = _rows(table, filters)
    if rows is None:
        raise RuleRejected("해석한 조건을 원본 값과 비교하지 못했습니다.")
    if not rows:
        raise RuleRejected("해석한 조건에 맞는 원본 행이 없습니다. 원본에 있는 이름으로 다시 요청해 주세요.")
    if len(rows) > MAX_CHANGES:
        raise RuleRejected(f"조건에 맞는 행이 {len(rows)}개로, 한 번에 바꿀 수 있는 {MAX_CHANGES}개를 넘습니다. "
                           "일부 행만 바뀌지 않도록 변경안을 만들지 않았습니다. 조건을 좁혀 나눠서 요청해 주세요.")
    columns = {column.id: column for column in table.columns}
    letter = re.search(r"([A-Z]+)\d+$", columns[target].header_reference.upper()).group(1)
    cells = {key(cell.sheet_name, cell.address): cell for item in index.rows
             if item.sheet_name == table.sheet_name for cell in item.cells}
    drafts = []
    for row in rows:
        cell = cells.get(key(table.sheet_name, f"{letter}{row.row_number}"))
        if cell is None:
            raise RuleRejected(f"{table.sheet_name}!{letter}{row.row_number}: 빈 셀이 있어 같은 계산을 적용할 수 없습니다.")
        drafts.append(WritebackChangeDraft(
            sheet_name=table.sheet_name, reference=cell.address, new_value=_new_value(rule, cell.value),
            reason=f"조건에 맞는 {len(rows)}개 행 모두에 같은 변경을 적용합니다. {rule.reading}"[:500]))
    conditions = ", ".join(f"‘{columns[item.column_id].display_header}’ {OPERATORS[item.operator]} {_shown(item.value)}"
                           .rstrip() for item in filters) or "조건 없이 표 전체"
    action = OPERATIONS[rule.operation].format(amount=rule.amount)
    reading = (f"‘{table.sheet_name}’ 표에서 {conditions}인 {len(rows)}개 행의 ‘{columns[target].display_header}’ 값을 "
               f"{action} 것으로 해석했습니다 ({rule.reading}). 승인 전에 대상 행과 열을 확인해 주세요.")
    return drafts, reading


COMPARE = {"greater_than": lambda a, b: a > b, "greater_than_or_equal": lambda a, b: a >= b,
           "less_than": lambda a, b: a < b, "less_than_or_equal": lambda a, b: a <= b}


def _rows(table, filters):
    """Source filters, plus date ranges ("2023년" → 2023-01-01 ≤ Date < 2024-01-01)."""
    dates = [item for item in filters if item.operator in COMPARE and _date(item.value) is not None]
    rows = filtered_rows(table, [item for item in filters if item not in dates])
    for item in dates if rows is not None else ():
        values = [_date(row.values.get(item.column_id)) for row in rows]
        if any(value is None for value in values):
            return None  # a blank or non-date cell cannot be placed inside a date range
        rows = [row for row, value in zip(rows, values) if COMPARE[item.operator](value, _date(item.value))]
    return rows


def _shown(value):
    if value is None:
        return ""
    return re.sub(r"[T ]00:00(?::00)?$", "", value) if isinstance(value, str) else str(value)


def _date(value):
    if isinstance(value, datetime):
        return value
    if isinstance(value, str) and re.fullmatch(r"\d{4}-\d{2}-\d{2}(?:[T ]\d{2}:\d{2}(?::\d{2})?)?", value.strip()):
        return datetime.fromisoformat(value.strip())
    return None


def _new_value(rule, current):
    if rule.operation == "set":
        number = as_number(rule.amount) if isinstance(current, (int, float)) and not isinstance(current, bool) else None
        return rule.amount if number is None or isinstance(rule.amount, bool) else _number(number)
    if rule.operation == "clear":
        return None
    amount, value = as_number(rule.amount), as_number(current)
    if amount is None or value is None or isinstance(current, bool):
        raise RuleRejected("숫자가 아닌 값에는 계산을 적용할 수 없습니다.")
    base = _clean(value)
    result = {"percent_increase": base * (1 + amount / 100), "percent_decrease": base * (1 - amount / 100),
              "add": base + amount, "subtract": base - amount, "multiply": base * amount}[rule.operation]
    return _number(result)


def _number(value: Decimal):
    value = value.normalize()
    return int(value) if value == value.to_integral_value() else float(value)


class RuledTargets:
    """Rows and column come from a rule checked against the source; values still need the request."""

    def __init__(self, instruction):
        # Several rules share one request ("10% 올리고 ... 5% 내려줘"), so each value is
        # checked against every stated value and calculation, not only the last clause.
        self.value_part = instruction

    def instruction_for(self, cell):
        return self.value_part, None

    def missing_risks(self, changes):
        return []
