import re
from dataclasses import dataclass

REFERENCE_BOX_PATTERN = re.compile(
    r"^(?P<sheet>.+)!(?P<start_column>[a-z]{1,3})(?P<start_row>\d+)"
    r"(?::(?P<end_column>[a-z]{1,3})(?P<end_row>\d+))?$"
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


def resolve_references(
    citations: set[str], available: set[str]
) -> tuple[set[str], set[str]]:
    resolved = set()
    unmatched = set()
    for citation in citations:
        matches = matching_references(citation, available)
        if matches:
            resolved.update(matches)
        else:
            unmatched.add(citation)
    return resolved, unmatched


def matching_references(citation: str, available: set[str]) -> set[str]:
    if citation in available:
        return {citation}
    cited_box = _box(citation)
    if cited_box is None or cited_box.area > MAX_CITATION_AREA:
        return set()
    parsed = [(reference, _box(reference)) for reference in available]
    contained = {
        reference
        for reference, candidate in parsed
        if candidate and _contains(cited_box, candidate)
    }
    if contained:
        return contained
    containing = [
        (reference, candidate)
        for reference, candidate in parsed
        if candidate and _contains(candidate, cited_box)
    ]
    if not containing:
        return set()
    smallest_area = min(candidate.area for _, candidate in containing)
    return {
        reference
        for reference, candidate in containing
        if candidate.area == smallest_area
    }


def _box(reference: str) -> ReferenceBox | None:
    match = REFERENCE_BOX_PATTERN.match(reference.casefold())
    if not match:
        return None
    start_column = _column_number(match.group("start_column"))
    start_row = int(match.group("start_row"))
    end_column = _column_number(match.group("end_column") or match.group("start_column"))
    end_row = int(match.group("end_row") or match.group("start_row"))
    return ReferenceBox(
        sheet=match.group("sheet"),
        min_column=min(start_column, end_column),
        min_row=min(start_row, end_row),
        max_column=max(start_column, end_column),
        max_row=max(start_row, end_row),
    )


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
    for character in column:
        result = result * 26 + ord(character) - ord("a") + 1
    return result
