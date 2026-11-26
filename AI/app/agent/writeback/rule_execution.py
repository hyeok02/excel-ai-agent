"""Turn a model's reading of an edit request into source cells and computed values.

The model reads the request ("쿠키 단가를 10% 올려줘") as one rule: a source table, the conditions that pick
its rows (Category = Cookies), one target column (UnitPrice) and one operation. It may translate the user's
words into source labels; it does not choose rows or values. Every name must exist in the source, the whole
table must be read, every matching row is taken, and each new value is computed from the operation. The
reading is shown to the reviewer, and the stated value or calculation is still checked against the request.
A rule that cannot be applied to every matching row is not applied at all; a row already at the value is left.
"""
import re
from decimal import Decimal

from app.agent.query.ambiguity_labels import resolve_unique_column
from app.agent.query.tabular_validation import validated_table
from app.agent.writeback.derived_values import _clean
from app.agent.writeback.models import WritebackChangeDraft
from app.agent.writeback.percent_amounts import stored_amount
from app.agent.writeback.ruled_targets import RuledTargets  # noqa: F401  (imported from here by callers)
from app.agent.writeback.rule_units import scaled_note, unit_note, unit_texts
from app.agent.writeback.rule_columns import compared_rows, copied_value, from_source, other_columns
from app.agent.writeback.references import key
from app.agent.writeback.rule_mentions import UNREAD, guessed_rows
from app.agent.writeback.rule_ranks import ranked_rows
from app.agent.writeback.rule_readings import rule_reading
from app.agent.writeback.rule_rows import matching_rows
from app.agent.writeback.rule_values import other_row_value, special, special_value
from app.agent.writeback.value_authorization import as_number
from app.agent.writeback.writeback_tables import writeback_tables

class RuleRejected(Exception):
    """The reading cannot be applied to every matching source row."""


class RuleNotFound(RuleRejected):
    """The reading names a table or column the source does not have; cell drafts may still apply."""


def rule_drafts(rule, summary, index, instruction=""):
    """(drafts, reading shown to the reviewer, (changed headers, all headers), copied cells) or RuleRejected."""
    every = writeback_tables(summary, index)
    tables = [table for table in every if table.id == rule.table_id] or [  # 'Sheet1' for its one table
        table for table in every if table.sheet_name == rule.table_id.rpartition("!")[0] or table.sheet_name == rule.table_id]
    if len(tables) != 1:
        raise RuleNotFound("해석한 표를 원본에서 찾지 못했습니다.")
    table = tables[0]
    targets = [resolve_unique_column(column, table) for column in (rule.target_column_id, *rule.also_target_column_ids)]
    filters = [item.model_copy(update={"column_id": resolve_unique_column(item.column_id, table)})
               for item in rule.filters]
    comparisons, source = other_columns(rule, table, resolve_unique_column)
    source = None if rule.value_row_filters else source  # value_column_id then names the other row's column
    if None in targets or any(None in (item.column_id, getattr(item, "other_column_id", "")) for item in
                              (*filters, *comparisons)) or (rule.value_column_id and source is None and not rule.value_row_filters):
        raise RuleNotFound("해석한 열 이름을 원본 표에서 하나로 찾지 못했습니다.")
    if source is not None and rule.operation not in ("set", "multiply", "add", "subtract", "percent_increase", "percent_decrease"):
        raise RuleRejected("다른 열의 값은 그 값으로 바꾸거나 그 값에서 계산하는 요청에만 가져올 수 있습니다.")
    targets = list(dict.fromkeys(targets))
    compared = {name for item in comparisons for name in (item.column_id, item.other_column_id)}
    # Columns read to pick rows or take values; a target's formula rows elsewhere (매출총이익) are never written.
    ranked = {resolve_unique_column(item.column_id, table) for item in (*rule.average_filters, *filter(None, [rule.rank]))}
    if not validated_table(table, index, {*(item.column_id for item in filters), *compared, *{source, *ranked} - {None}}):
        raise RuleRejected("표 전체를 원본에서 확인하지 못해 조건에 맞는 모든 행을 바꾼다고 보장할 수 없습니다.")
    if guessed := guessed_rows(rule, filters, table, instruction):  # a rank's row picked by the reading itself
        raise RuleRejected(f"{UNREAD} ‘가장·상위·평균’ 같은 순위 조건이 해석에 빠졌습니다. 요청에 없는 ‘{', '.join(guessed)}’ 행을 골랐습니다.")
    rows = matching_rows(table, filters)
    if rows and comparisons:  # 재고 < 안전재고, row by row
        rows = compared_rows(rows, comparisons)
    if rows is None:
        raise RuleRejected("해석한 조건을 원본 값과 비교하지 못했습니다.")
    rows, problem = ranked_rows(rows, rule, resolve_unique_column, table)  # 가장 비싼, 상위 3명, 평균보다 낮은
    if problem:
        raise RuleRejected(problem)
    if not rows:
        raise RuleRejected("해석한 조건에 맞는 원본 행이 없습니다. 원본에 있는 이름으로 다시 요청해 주세요.")
    columns = {column.id: column for column in table.columns}
    cells = {key(cell.sheet_name, cell.address): cell for item in index.rows
             if item.sheet_name == table.sheet_name for cell in item.cells}
    letter = lambda column: re.search(r"([A-Z]+)\d+$", columns[column].header_reference.upper()).group(1)  # noqa: E731
    try:
        other = rule.value_row_filters and other_row_value(rule, table, resolve_unique_column, lambda address: cells.get(
            key(table.sheet_name, address)), letter, instruction, targets[0])
        drafts, copied = [], {}
        for row in rows:
            for target in targets:
                _draft(rule, row, (table, target, letter, cells, source, other, len(rows)), instruction, (drafts, copied))
    except ValueError as error:
        raise RuleRejected(str(error)) from None
    if not drafts:
        raise RuleRejected("조건에 맞는 행이 이미 모두 요청한 값입니다.")
    reading = rule_reading(rule, table, (filters, comparisons, rows, targets, source, other and other[1]), drafts, cells,
                           resolve_unique_column, instruction)
    headers = [columns[target].display_header for target in targets]
    return drafts, reading, (headers, [column.display_header for column in table.columns], table), copied


def _draft(rule, row, place, instruction, found):
    """One target cell's change; a value the request cannot state as a number is checked and explained here."""
    (table, target, letter, cells, source, other, count), (drafts, copied) = place, found
    address = f"{letter(target)}{row.row_number}"
    cell = cells.get(key(table.sheet_name, address))
    if cell is None and rule.operation not in ("set", "clear", "replace_text"):
        raise ValueError(f"{table.sheet_name}!{address}: 빈 셀이 있어 같은 계산을 적용할 수 없습니다.")
    note = None
    if other:  # another row's value: 생수's 단가 for 우유
        value, note = other
    elif source is not None:  # the other column's value on this row: 안전재고 → 재고
        origin = f"{letter(source)}{row.row_number}"
        header = next(column.display_header for column in table.columns if column.id == source)
        value, problem = copied_value(cells.get(key(table.sheet_name, origin)), header, instruction)
        if problem:
            raise ValueError(problem)
        value, note = from_source(rule, value, f"같은 행 ‘{header}’({origin}) 값 {value}", instruction, _new_value)
    elif special(rule):  # text, rounding, a date moved
        value, note = special_value(rule, cell, instruction)
    else:
        value = None if rule.operation == "clear" else _new_value(rule, cell, instruction) if cell else rule.amount
        column = next(column for column in table.columns if column.id == target)
        texts = unit_texts(table, column, cells)  # 90 in 영업이익(억원) for '90억원'; '1,000만원씩' in 집행액(만원)
        note = unit_note(texts, value, instruction) if rule.operation == "set" else cell and scaled_note(
            texts, cell.value, value, instruction)
    if value == (current := getattr(cell, "value", None)) and isinstance(value, bool) == isinstance(current, bool):
        return  # already so: a blank to clear, a Discount already 10%
    if note:
        copied[key(table.sheet_name, address)] = note
    drafts.append(WritebackChangeDraft(  # a blank cell is filled as written ('미정' where 공급사 is empty)
        sheet_name=table.sheet_name, reference=address, new_value=value,
        reason=f"조건에 맞는 {count}개 행 모두에 같은 변경을 적용합니다. {rule.reading}"[:500]))
def _new_value(rule, cell, instruction):
    current = cell.value
    if rule.operation == "set":
        numeric = isinstance(current, (int, float)) and not isinstance(current, bool)
        number = stored_amount(rule.amount, cell, instruction) if numeric else None
        return rule.amount if number is None else _number(number)
    if rule.operation == "clear":
        return None
    amount, value = as_number(rule.amount), as_number(current)
    if amount is None:  # '가격 좀 올려줘': how much is not said
        raise RuleRejected("얼마나 바꿀지(값, %, 금액)가 요청에 없습니다. 예: ‘10% 올려줘’, ‘500원씩 올려줘’")
    if value is None or isinstance(current, bool):
        raise RuleRejected("숫자가 아닌 값에는 계산을 적용할 수 없습니다.")
    base = _clean(value)
    result = {"percent_increase": base * (1 + amount / 100), "percent_decrease": base * (1 - amount / 100),
              "add": base + amount, "subtract": base - amount, "multiply": base * amount}[rule.operation]
    return _number(result)


def _number(value: Decimal):
    value = value.normalize()
    return int(value) if value == value.to_integral_value() else float(value)
