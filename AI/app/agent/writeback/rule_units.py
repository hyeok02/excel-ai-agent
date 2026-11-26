"""A value written in the unit its column header names: '90억원' is 90 in 영업이익(억원).

The request's number carries the scale (90억 = 9,000,000,000) while the column already counts in 억원, so the
stated value checked against the request is the number before the scale word, and only for a column whose
header names that same scale. A column without it still has to take 9,000,000,000.
"""
import re

from app.agent.writeback.value_authorization import as_number

SCALES = ("백만", "조", "억", "만", "천")


def unit_note(header, value, instruction):
    """The reason a number is the request's value in the column's unit, or None."""
    number = as_number(value)
    if number is None or isinstance(value, bool):
        return None
    for scale in SCALES:
        if re.search(rf"[(\[（]\s*{scale}", str(header)) is None:
            continue
        for match in re.finditer(rf"(?<![\d.,])(\d[\d,]*(?:\.\d+)?)\s*{scale}(?!\d)", instruction):
            if as_number(match.group(1)) == number:
                return f"요청의 {match.group(0).strip()}을 ‘{header}’ 열 단위로 적은 값 {match.group(1)}"
    return None
