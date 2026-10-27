"""Separate descriptive headers from a labeled series-identifier metadata row."""
import re

from openpyxl.utils import get_column_letter, range_boundaries

_CODE = re.compile(r"(?=[A-Za-z0-9_]*[A-Za-z])(?=[A-Za-z0-9_]*\d)[A-Za-z0-9_]{2,20}")
_MARKER = re.compile(
    r"(?:(?:dataset|series|variable|field|indicator|column|statistical)\s+)?"
    r"(?:identifiers?(?:\s+codes?)?|codes?|cdid|id)|"
    r"(?:(?:자료|시계열|변수|항목|열|데이터셋)\s*)?(?:식별자|식별\s*코드|코드)", re.I,
)
_DETAIL_MARKER = re.compile(
    r"(?:pre\s*)?units?|(?:last\s+)?release\s+date|next\s+release(?:\s+date)?|"
    r"(?:important\s+)?notes?|frequency|source|단위|발표일|공표일|주기|출처|주석", re.I,
)
MAX_METADATA_ROWS = 8


def _value(cells, column, row):
    cell = cells.get(f"{get_column_letter(column)}{row}", {})
    return cell.get("cached_value") if cell.get("formula") else cell.get("value")


def _series_metadata(cells, left, row, right):
    values = [_value(cells, number, row) for number in range(left, right + 1)]
    codes = [number for number in range(left, right + 1)
             if isinstance(_value(cells, number, row), str)
             and _CODE.fullmatch(_value(cells, number, row).strip())]
    if len(codes) < 2 or not any(isinstance(value, str) and _MARKER.fullmatch(value.strip()) for value in values):
        return False
    if any(value not in (None, "") and not isinstance(value, str) for value in values):
        return False
    return all(isinstance(_value(cells, number, row - 1), str)
               and len(_value(cells, number, row - 1).strip()) > len(_value(cells, number, row).strip())
               for number in codes)


def recover_series_header_range(reference, cells):
    """Restore the human header and identity axis above bold identifier codes.

The explicit code-row marker prevents treating arbitrary textual records as
metadata. A neighboring identity column is retained only when both its human
header and the metadata marker occupy those same source rows.
"""
    left, top, right, bottom = range_boundaries(reference)
    if top <= 1:
        return reference
    first = left
    if left > 1:
        marker = _value(cells, left - 1, top)
        label = _value(cells, left - 1, top - 1)
        if isinstance(marker, str) and _MARKER.fullmatch(marker.strip()) and isinstance(label, str) and label.strip():
            first -= 1
    if not _series_metadata(cells, first, top, right):
        return reference
    if not all(isinstance(_value(cells, number, top - 1), str)
               and _value(cells, number, top - 1).strip() for number in range(first, right + 1)):
        return reference
    return f"{get_column_letter(first)}{top - 1}:{get_column_letter(right)}{bottom}"


def series_metadata_rows(reference, cells):
    left, top, right, bottom = range_boundaries(reference)
    if top >= bottom or not _series_metadata(cells, left, top + 1, right):
        return frozenset()
    rows = {top + 1}
    for row in range(top + 2, min(bottom, top + MAX_METADATA_ROWS) + 1):
        if not detail_metadata_row(cells, left, row, right):
            break
        rows.add(row)
    return frozenset(rows)


def detail_metadata_row(cells, left, row, right):
    label = _value(cells, left, row)
    return (isinstance(label, str) and bool(_DETAIL_MARKER.fullmatch(label.strip()))
            and all(_value(cells, number, row) in (None, "")
                    or isinstance(_value(cells, number, row), str)
                    for number in range(left + 1, right + 1)))


def series_identifiers(sheet, reference, cells, column, metadata=None):
    left, top, right, _ = range_boundaries(reference)
    if top + 1 not in (metadata if metadata is not None else series_metadata_rows(reference, cells)):
        return ()
    address = f"{column}{top + 1}"
    raw = cells.get(address, {})
    value = raw.get("cached_value") if raw.get("formula") else raw.get("value")
    if isinstance(value, str) and _CODE.fullmatch(value.strip()):
        return ((f"{sheet}!{address}", value.strip()),)
    return ()
