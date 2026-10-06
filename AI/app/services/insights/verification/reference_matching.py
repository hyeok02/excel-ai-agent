import re
from dataclasses import dataclass

REFERENCE_BOX_PATTERN = re.compile(
    r"^(?P<sheet>.+)!(?P<start_column>[a-z]{1,3})(?P<start_row>\d+)"
    r"(?::(?P<end_column>[a-z]{1,3})(?P<end_row>\d+))?$"
)
MAX_CITATION_AREA = 10_000
MAX_RELATED_COLUMN_GAP = 2
MAX_RELATED_ROW_GAP = 12


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
    # A smaller citation cannot borrow values from a larger enclosing sample.
    return set()


def related_references(source: str, targets: set[str]) -> bool:
    """Relate labels to nearby table evidence without crossing worksheet sections."""
    source_box = _box(source)
    if source_box is None:
        return False
    for target in targets:
        target_box = _box(target)
        if (target_box and source_box.sheet == target_box.sheet
                and _column_gap(source_box, target_box) <= MAX_RELATED_COLUMN_GAP
                and _row_gap(source_box, target_box) <= MAX_RELATED_ROW_GAP):
            return True
    return False


def overlapping_references(source: str, targets: set[str]) -> bool:
    """True when a proposed label is itself part of narrated table evidence."""
    source_box = _box(source)
    if source_box is None:
        return False
    return any(
        target_box is not None
        and source_box.sheet == target_box.sheet
        and _column_gap(source_box, target_box) == 0
        and _row_gap(source_box, target_box) == 0
        for target in targets
        if (target_box := _box(target)) is not None
    )


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


def _column_gap(left: ReferenceBox, right: ReferenceBox) -> int:
    if left.max_column < right.min_column:
        return right.min_column - left.max_column
    if right.max_column < left.min_column:
        return left.min_column - right.max_column
    return 0


def _row_gap(top: ReferenceBox, bottom: ReferenceBox) -> int:
    if top.max_row < bottom.min_row:
        return bottom.min_row - top.max_row
    if bottom.max_row < top.min_row:
        return top.min_row - bottom.max_row
    return 0


def _column_number(column: str) -> int:
    result = 0
    for character in column:
        result = result * 26 + ord(character) - ord("a") + 1
    return result
