from bisect import bisect_left, bisect_right
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from types import MappingProxyType

# Geometry lives in reference_boxes; module-level names keep call sites patchable.
from app.services.insights.verification.reference_boxes import (  # noqa: F401
    REFERENCE_BOX_PATTERN, ReferenceBox, _box, _column_gap, _contains, _row_gap,
)

MAX_CITATION_AREA = 10_000
MAX_RELATED_COLUMN_GAP = 2
MAX_RELATED_ROW_GAP = 12


@dataclass(frozen=True)
class _SheetReferences:
    start_rows: tuple[int, ...]
    references: tuple[tuple[str, ReferenceBox], ...]


@dataclass(frozen=True)
class ReferenceIndex:
    """Parsed snapshot reused only within the owning evidence index/request."""

    _sheets: Mapping[str, _SheetReferences]

    @classmethod
    def from_references(cls, available: Iterable[str]) -> "ReferenceIndex":
        sheets: dict[str, list[tuple[str, ReferenceBox]]] = {}
        for reference in available:
            box = _box(reference)
            if box is not None:
                sheets.setdefault(box.sheet, []).append((reference, box))
        prepared = {}
        for sheet, references in sheets.items():
            references.sort(key=lambda item: item[1].min_row)
            prepared[sheet] = _SheetReferences(
                start_rows=tuple(box.min_row for _, box in references),
                references=tuple(references),
            )
        return cls(MappingProxyType(prepared))

    def _contained(self, cited_box: ReferenceBox) -> set[str]:
        sheet = self._sheets.get(cited_box.sheet)
        if sheet is None:
            return set()
        start = bisect_left(sheet.start_rows, cited_box.min_row)
        end = bisect_right(sheet.start_rows, cited_box.max_row)
        return {
            reference
            for reference, candidate in sheet.references[start:end]
            if _contains(cited_box, candidate)
        }


def resolve_references(
    citations: set[str], available: set[str] | ReferenceIndex
) -> tuple[set[str], set[str]]:
    resolved = set()
    unmatched = set()
    if not citations:
        return resolved, unmatched
    prepared = (
        available if isinstance(available, ReferenceIndex)
        else ReferenceIndex.from_references(available)
    )
    for citation in citations:
        matches = matching_references(citation, prepared)
        if matches:
            resolved.update(matches)
        else:
            unmatched.add(citation)
    return resolved, unmatched


def matching_references(
    citation: str, available: set[str] | ReferenceIndex
) -> set[str]:
    cited_box = _box(citation)
    if cited_box is None or cited_box.area > MAX_CITATION_AREA:
        return set()
    # A smaller citation cannot borrow values from a larger enclosing sample.
    if isinstance(available, ReferenceIndex):
        return available._contained(cited_box)
    # Grounding checks commonly compare a single required reference. Do not
    # allocate/sort an index for these one-off comparisons.
    return {
        reference for reference in available
        if (candidate := _box(reference)) is not None
        and _contains(cited_box, candidate)
    }


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
