import re
from dataclasses import dataclass

REFERENCE_PATTERN = re.compile(
    r"(?:'((?:[^']|'')+)'|([^\s!,:;=\"'\[\]{}]+))!\$?([A-Z]{1,3})\$?(\d+)"
    r"(?::\$?([A-Z]{1,3})\$?(\d+))?",
    re.I,
)
CELL_RANGE_PATTERN = re.compile(
    r"\$?([A-Z]{1,3})\$?(\d+)(?::\$?([A-Z]{1,3})\$?(\d+))?",
    re.I,
)
MAX_CITATION_AREA = 10_000


@dataclass(frozen=True)
class ReferenceBox:
    sheet: str
    min_column: int
    min_row: int
    max_column: int
    max_row: int

    @property
    def area(self) -> int:
        return (self.max_column - self.min_column + 1) * (
            self.max_row - self.min_row + 1
        )


def extract_references(value: str) -> list[str]:
    return [
        normalized
        for match in REFERENCE_PATTERN.finditer(value)
        if (normalized := _normalize_match(match))
    ]


def normalize_reference(value: object) -> str | None:
    parsed = _parse_reference(str(value))
    return _canonical(*parsed) if parsed else None


def matching_references(citation: str, available: set[str]) -> set[str]:
    cited = _box(citation)
    if cited is None or cited.area > MAX_CITATION_AREA:
        return set()
    return {
        reference
        for reference in available
        if (candidate := _box(reference)) and _contains(cited, candidate)
    }


def _normalize_match(match: re.Match[str]) -> str:
    quoted = match.group(1)
    sheet = quoted.replace("''", "'") if quoted is not None else match.group(2)
    return _canonical(
        sheet,
        match.group(3),
        match.group(4),
        match.group(5),
        match.group(6),
    )


def _box(reference: str) -> ReferenceBox | None:
    parsed = _parse_reference(reference)
    if parsed is None:
        return None
    sheet, start, start_row, end, end_row = parsed
    start_column = _column_number(start)
    end_column = _column_number(end or start)
    start_row = int(start_row)
    end_row = int(end_row or start_row)
    return ReferenceBox(
        sheet.casefold(),
        min(start_column, end_column),
        min(start_row, end_row),
        max(start_column, end_column),
        max(start_row, end_row),
    )


def _parse_reference(value: str) -> tuple[str, str, str, str | None, str | None] | None:
    sheet, separator, cells = value.strip().rpartition("!")
    match = CELL_RANGE_PATTERN.fullmatch(cells)
    if not separator or not sheet.strip() or not match:
        return None
    sheet = sheet.strip()
    if len(sheet) >= 2 and sheet.startswith("'") and sheet.endswith("'"):
        sheet = sheet[1:-1].replace("''", "'")
    if not sheet.strip():
        return None
    return sheet, match.group(1), match.group(2), match.group(3), match.group(4)


def _canonical(sheet, start, start_row, end, end_row) -> str:
    suffix = f":{end}{end_row}" if end else ""
    return f"{sheet.strip()}!{start}{start_row}{suffix}".casefold()


def _contains(outer: ReferenceBox, inner: ReferenceBox) -> bool:
    return (
        outer.sheet == inner.sheet
        and outer.min_column <= inner.min_column
        and outer.min_row <= inner.min_row
        and outer.max_column >= inner.max_column
        and outer.max_row >= inner.max_row
    )


def _column_number(column: str) -> int:
    result = 0
    for character in column.casefold():
        result = result * 26 + ord(character) - ord("a") + 1
    return result
