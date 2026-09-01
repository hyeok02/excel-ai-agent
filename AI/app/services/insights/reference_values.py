import json
import re
from typing import Any, Protocol

from app.services.insights.numeric_validation import numbers

CELL_RANGE_PATTERN = re.compile(r"^\$?[A-Z]{1,3}\$?\d+(?::\$?[A-Z]{1,3}\$?\d+)?$")


class ReferenceNumberIndex(Protocol):
    references: set[str]
    reference_numbers: dict[str, set]


def index_reference_numbers(
    index: ReferenceNumberIndex,
    sheet: Any,
    sheet_name: str,
    extract_references,
    normalize_reference,
) -> None:
    for record in _walk_dicts(sheet):
        references = _record_references(
            record, sheet_name, extract_references, normalize_reference
        )
        if not references:
            continue
        record_numbers = numbers(
            json.dumps(_claim_values(record), ensure_ascii=False, default=str)
        )
        for reference in references:
            index.references.add(reference)
            index.reference_numbers.setdefault(reference, set()).update(record_numbers)


def _walk_dicts(value: Any):
    if isinstance(value, dict):
        yield value
        for item in value.values():
            yield from _walk_dicts(item)
    elif isinstance(value, list):
        for item in value:
            yield from _walk_dicts(item)


def _record_references(record, sheet_name, extract_references, normalize_reference):
    candidates: list[str] = []
    for key in (
        "location",
        "reference",
        "table_range",
        "anchor_cell",
        "evidence",
        "cell",
    ):
        value = record.get(key)
        if isinstance(value, list):
            candidates.extend(str(item) for item in value)
        elif value:
            candidates.append(str(value))
    references: set[str] = set()
    for candidate in candidates:
        parsed = extract_references(candidate)
        if not parsed and CELL_RANGE_PATTERN.match(candidate):
            normalized = normalize_reference(f"{sheet_name}!{candidate}")
            parsed = {normalized} if normalized else set()
        references.update(parsed)
    return references


def _claim_values(value: Any) -> Any:
    if isinstance(value, dict):
        excluded = {
            "anchor_cell",
            "cell",
            "evidence",
            "location",
            "reference",
            "references",
            "table_range",
        }
        return {
            key: _claim_values(item)
            for key, item in value.items()
            if key not in excluded
        }
    if isinstance(value, list):
        return [_claim_values(item) for item in value]
    return value
