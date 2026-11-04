"""An "every X" request reaches every matching source row, or none of them.

The model sees only a sample of candidate rows, so its draft for "모든 Carrot 단가를
10% 올려줘" may cover 7 of 64 Carrot rows. Showing that as ready would let a
reviewer approve a partial edit as if it were complete. From the accepted draft
this derives the rule (one column of one table, the source labels the request
names, one stated value or one stated calculation), re-applies it here to every
data row of that table carrying those labels and computes each value itself.
"""
import re
from decimal import Decimal

from app.agent.tools.workbook_header_index import detect_header_rows
from app.agent.writeback.change_direction import direction_after
from app.agent.writeback.derived_values import (
    AMOUNT, HALF, KOREAN_MULTIPLE, MAGNITUDE, MULTIPLE, PERCENT, TRANSITION, _clean,
)
from app.agent.writeback.models import WritebackChangeDraft
from app.agent.writeback.natural_operations import ASSIGNMENT
from app.agent.writeback.references import column_number
from app.agent.writeback.target_semantics import ALL, LEADING_ALL, _label_matches
from app.agent.writeback.value_authorization import as_number, value_is_authorized

NO_RULE = "요청한 행 전체에 같은 값이나 계산을 적용할 수 없어 일부 행만 바꾸지 않았습니다."


def requests_every_row(instruction):
    parts = ASSIGNMENT.split(instruction, maxsplit=1)
    return bool(ALL.search(parts[0]) or len(parts) == 2 and LEADING_ALL.match(parts[1]))


def every_row_drafts(instruction, changes, index):
    """(drafts for every matching row, blocking reason); (None, None) keeps the draft."""
    if (not changes or not requests_every_row(instruction) or any(c.change_type != "value" for c in changes)
            or len({(c.sheet_name, column_number(c.reference)) for c in changes}) != 1):
        return None, None
    sheet, column = changes[0].sheet_name, column_number(changes[0].reference)
    rows = {row.row_number: row for row in index.rows if row.sheet_name == sheet}
    numbers = [int(re.search(r"\d+", change.reference).group()) for change in changes]
    if any(number not in rows for number in numbers):
        return None, None
    prefix = ASSIGNMENT.split(instruction, maxsplit=1)[0]
    labels = set.intersection(*(_labels(rows[number], prefix) for number in numbers))
    low, high = _table_rows(index, sheet, min(numbers), max(numbers))
    matching = [row for number, row in sorted(rows.items()) if low < number < high
                and _target(row, column) is not None and labels <= _labels(row, prefix)]
    constant = changes[0].new_value if len({repr(c.new_value) for c in changes}) == 1 and value_is_authorized(
        changes[0].new_value, instruction) else None
    drafts = []
    for row in matching:
        cell = _target(row, column)
        result = None if constant is not None else computed_value(cell.value, instruction)
        if constant is None and result is None:
            return None, NO_RULE
        drafts.append(WritebackChangeDraft(
            sheet_name=sheet, reference=cell.address, new_value=constant if result is None else _number(result),
            reason=f"요청 조건에 맞는 {len(matching)}개 행 모두에 같은 {'값' if result is None else '계산'}을 적용합니다."))
    return drafts, None


def computed_value(current_value, instruction):
    """The one calculation the request states, applied to this value; None if absent."""
    current = as_number(current_value)
    if current is None or TRANSITION.search(instruction):
        return None
    base = _clean(current)
    for match in PERCENT.finditer(instruction):
        if sign := direction_after(instruction, match.end()):
            return base * (1 + sign * Decimal(match.group(1)) / 100)
    for match in MULTIPLE.finditer(instruction):
        if (size := Decimal(KOREAN_MULTIPLE.get(match.group(1), 0) or match.group(1))) > 0:
            return base * size
    if any(word in instruction for word in HALF):
        return base / 2
    for match in AMOUNT.finditer(instruction):
        amount = as_number(match.group(1))
        if (sign := direction_after(instruction, match.end())) and amount:
            return base + sign * amount * MAGNITUDE.get(match.group(2) or "", 1)
    return None


def _labels(row, prefix):
    return {(column_number(cell.address), str(cell.value).casefold())
            for cell in row.cells if _label_matches(cell.value, prefix)}


def _target(row, column):
    cell = next((item for item in row.cells if column_number(item.address) == column), None)
    return cell if cell is not None and not cell.formula else None


def _table_rows(index, sheet, first, last):
    """Rows strictly between the header above the change and the next header below it."""
    header_rows = detect_header_rows(index.rows).header_rows.get(sheet, set())
    above = [number for number in header_rows if number < first]
    below = [number for number in header_rows if number > last]
    return (max(above) if above else 0), (min(below) if below else float("inf"))


def _number(value):
    value = value.normalize()
    return int(value) if value == value.to_integral_value() else float(value)
