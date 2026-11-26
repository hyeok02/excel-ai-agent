"""New values that are neither a stated number nor a calculation on it, computed here from the source cell.

Text put before or after a name or replaced inside it ('[단종]', 'mail.com' → 'example.com'), a number rounded
('소수 첫째 자리에서 반올림'), a date moved ('2주 미뤄줘'), another row's value ('생수 단가와 같게'). Each is kept
only when the request itself says it: the text, the places and the rounding word, the period and its direction,
the other row's name. A cell the operation does not fit stops the rule (ValueError) rather than being skipped.
"""
import calendar
import re
from datetime import datetime, timedelta
from decimal import ROUND_CEILING, ROUND_FLOOR, ROUND_HALF_UP, Decimal

from app.agent.writeback.rule_rows import matching_rows
from app.agent.writeback.rounding_words import ROUNDING, rounding_places
from app.agent.writeback.rule_mentions import named_value
from app.agent.writeback.time_periods import moved_by

TEXT = {"prepend_text", "append_text", "replace_text"}
MODES = {"round": ROUND_HALF_UP, "round_up": ROUND_CEILING, "round_down": ROUND_FLOOR}


def special(rule):
    return rule.operation in TEXT | MODES.keys() or rule.amount_unit is not None or bool(rule.value_row_filters)


def other_row_value(rule, table, resolve, cells, letter, instruction, target):
    """(value, note) from the one row value_row_filters pick: 생수's 단가 for '우유 단가를 생수 단가와 같게'."""
    filters = [item.model_copy(update={"column_id": resolve(item.column_id, table)}) for item in rule.value_row_filters]
    rows = matching_rows(table, filters) if all(item.column_id for item in filters) else None
    if not rows or len(rows) != 1:
        raise ValueError("값을 가져올 행을 원본에서 하나로 찾지 못했습니다.")
    names = [str(item.value) for item in filters]
    if not all(named_value(item.value, instruction) or "같은 날" in instruction and _date_like(item.value) for item in filters):
        raise ValueError(f"값을 가져올 행 ‘{', '.join(names)}’이 요청에 적혀 있지 않습니다.")
    column = resolve(rule.value_column_id, table) if rule.value_column_id else target
    cell = cells(f"{letter(column)}{rows[0].row_number}")
    if cell is None or cell.value in (None, ""):
        raise ValueError(f"‘{', '.join(names)}’ 행에 가져올 값이 없습니다.")
    return cell.value, f"‘{', '.join(names)}’ 행({cell.address})의 값 {cell.value}"


def _date_like(value):
    return isinstance(value, datetime) or isinstance(value, str) and re.match(r"\d{4}-\d{2}-\d{2}", value) is not None


def special_value(rule, cell, instruction):
    """(value, note) for a text, rounding or date operation on one source cell."""
    current = getattr(cell, "value", None)
    if rule.operation in TEXT:
        return _text(rule, current, instruction)
    if rule.operation in MODES:
        return _rounded(rule, current, instruction)
    return _moved(rule, current, instruction)


def _text(rule, current, instruction):
    text = "" if rule.amount is None else str(rule.amount)
    words = [text] + ([rule.find_text or ""] if rule.operation == "replace_text" else [])
    if not all(word and word.casefold() in instruction.casefold() for word in words):
        raise ValueError("붙이거나 바꿀 글자가 요청에 적혀 있지 않습니다.")
    if rule.operation == "replace_text" and not (isinstance(current, str) and rule.find_text in current):
        return current, None  # nothing to replace in this cell (a blank e-mail): left as it is
    if not isinstance(current, str):
        raise ValueError("글자가 아닌 셀에는 글자를 붙일 수 없습니다.")
    if rule.operation == "replace_text":
        return current.replace(rule.find_text, text), f"‘{rule.find_text}’ → ‘{text}’"
    value = text + current if rule.operation == "prepend_text" else current + text
    return value, f"‘{current}’에 ‘{text}’ 붙임"


def _rounded(rule, current, instruction):
    stated = rounding_places(instruction)  # the request's places decide, not the reading: '첫째 자리에서' keeps 0
    places = next(iter(stated)) if len(stated) == 1 else int(rule.amount) if str(rule.amount).lstrip("-").isdigit() else None
    if not ROUNDING[rule.operation].search(instruction) or places not in stated:
        raise ValueError("반올림·올림·내림 방법이나 자리 수를 요청에서 확인하지 못했습니다.")
    if not isinstance(current, (int, float)) or isinstance(current, bool):
        raise ValueError("숫자가 아닌 값은 반올림할 수 없습니다.")
    value = Decimal(str(current)).quantize(Decimal(1).scaleb(-places), rounding=MODES[rule.operation])
    value = int(value) if value == value.to_integral_value() else float(value)
    return value, f"{current} → {value}"


def _moved(rule, current, instruction):
    try:
        when = datetime.fromisoformat(str(current))
    except ValueError:
        raise ValueError("날짜가 아닌 값은 기간만큼 옮길 수 없습니다.") from None
    amount = int(rule.amount) if str(rule.amount).isdigit() else None
    sign = {"add": 1, "subtract": -1}.get(rule.operation)
    if amount is None or sign is None or not moved_by(instruction, amount, rule.amount_unit, sign):
        raise ValueError("옮길 기간이나 방향을 요청에서 확인하지 못했습니다.")
    if rule.amount_unit in ("days", "weeks"):
        moved = when + sign * timedelta(days=amount * (7 if rule.amount_unit == "weeks" else 1))
    else:
        months = when.month - 1 + sign * amount * (12 if rule.amount_unit == "years" else 1)
        year, month = when.year + months // 12, months % 12 + 1
        moved = when.replace(year=year, month=month, day=min(when.day, calendar.monthrange(year, month)[1]))
    value = moved.date().isoformat() if moved.time() == datetime.min.time() else moved.isoformat()
    return value, f"{when.date()} → {value}"
