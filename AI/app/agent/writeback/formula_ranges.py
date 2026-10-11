"""수식이 가리키는 범위를 시트까지 함께 읽는다.

한 셀을 고치면 무엇이 따라 바뀌는지 보여 주는 화면이 쓰는 코드다. 범위가
다른 시트에 적혀 있거나(`Data!B2:B20`) 열 전체를 가리키면(`A:A`) 그 범위를
읽지 못해 "영향 없음"으로 나갔다. 승인 화면이 영향 없다고 적어 두고 합계가
조용히 바뀌는 쪽이, 아예 못 읽는 쪽보다 나쁘다.
"""
import re

from openpyxl.utils.cell import range_boundaries

PART = r"[A-Z]{1,3}[0-9]{1,7}|[A-Z]{1,3}|[0-9]{1,7}"
SHEET_RANGE = re.compile(
    rf"(?:'([^']+)'|([A-Z_][A-Z0-9_. ]*))!({PART}):({PART})(?![\w(])", re.I
)
PLAIN_RANGE = re.compile(rf"(?<![!\w])({PART}):({PART})(?![\w(])", re.I)


def sheet_ranges(formula: str) -> list[tuple[str, str]]:
    """Ranges written with a sheet in front, as (sheet, "start:end")."""
    return [
        (quoted or bare, f"{start}:{end}")
        for quoted, bare, start, end in SHEET_RANGE.findall(formula)
    ]


def plain_ranges(formula: str) -> list[str]:
    """Ranges with no sheet in front — they mean the formula's own sheet."""
    spans = [match.span() for match in SHEET_RANGE.finditer(formula)]
    return [
        f"{start}:{end}"
        for match in PLAIN_RANGE.finditer(formula)
        if not any(low <= match.start() < high for low, high in spans)
        for start, end in [match.groups()]
    ]


def covers(span: str, column: int, row: int) -> bool:
    """열 전체(A:A)와 행 전체(5:5)는 한쪽 경계가 비어 있어 따로 다룬다."""
    try:
        min_column, min_row, max_column, max_row = range_boundaries(span.upper())
    except (ValueError, TypeError):
        return False
    return _within(column, min_column, max_column) and _within(row, min_row, max_row)


def _within(value: int, low: int | None, high: int | None) -> bool:
    return (low is None or low <= value) and (high is None or value <= high)
