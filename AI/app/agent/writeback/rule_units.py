"""A value written in the unit its column header names: '90억원' is 90 in 영업이익(억원).

The request's number carries the scale (90억 = 9,000,000,000) while the column already counts in 억원, so the
stated value checked against the request is the number before the scale word, and only for a column whose
header names that same scale. A column without it still has to take 9,000,000,000.
"""
import re

from openpyxl.utils import range_boundaries
from openpyxl.utils.cell import get_column_letter

from app.agent.writeback.references import key
from app.agent.writeback.korean_numbers import plain_numbers
from app.agent.writeback.value_authorization import _stated_numbers, as_number

SCALES = ("백만", "조", "억", "만", "천")
MAGNITUDE = {"백만": 10 ** 6, "조": 10 ** 12, "억": 10 ** 8, "만": 10 ** 4, "천": 10 ** 3}


def unit_texts(table, column, cells):
    """Where a column's unit is written: its header, the headers above it, the table's title rows."""
    left, top, right, _ = range_boundaries(table.reference)
    above = [cell.value for row in range(max(1, top - 2), top) for number in range(left, right + 1)
             if isinstance(getattr(cell := cells.get(key(table.sheet_name, f"{get_column_letter(number)}{row}")),
                                   "value", None), str)]
    return [column.display_header, *(label for _, label in column.header_path),
            *(text for _, text in table.context), *above]


def unit_note(texts, value, instruction):
    """The reason a number is the request's value in the column's unit, or None."""
    number = as_number(value)
    if number is None or isinstance(value, bool):
        return None
    header = " ".join(str(text) for text in texts)
    for scale in SCALES:
        if re.search(rf"[(\[（]\s*(?:단위\s*[:：]?\s*)?{scale}", header) is None:
            continue
        if number * MAGNITUDE[scale] in _stated_numbers(plain_numbers(instruction)):  # 1억 2천만원 = 12000 만원
            return f"요청한 금액을 ‘{texts[0]}’ 열 단위({scale}원)로 적은 값 {value}"
    return None
