import re
from typing import Any, Protocol

from app.services.insights.numeric_validation import numbers

CELL_RANGE_PATTERN = re.compile(r"^\$?[A-Z]{1,3}\$?\d+(?::\$?[A-Z]{1,3}\$?\d+)?$")


class ReferenceNumberIndex(Protocol):
    references: set[str]
    reference_numbers: dict[str, set]
    reference_text: dict[str, list[str]]


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
        texts = list(_source_strings(_claim_values(record)))
        record_numbers = numbers(" ".join(texts))
        for reference in references:
            index.references.add(reference)
            index.reference_numbers.setdefault(reference, set()).update(record_numbers)
            index.reference_text.setdefault(reference, []).extend(texts)


def _walk_dicts(value: Any):
    if isinstance(value, dict):
        yield value
        for item in value.values():
            yield from _walk_dicts(item)
    elif isinstance(value, list):
        for item in value:
            yield from _walk_dicts(item)


def _source_strings(value):
    if isinstance(value, list):
        for item in value:
            yield from _source_strings(item)
    elif value is not None:
        yield str(value)


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
        source_fields = {
            "value", "values", "label", "headers", "header_path", "metric",
            "earliest_period", "latest_period", "earliest_value", "latest_value",
            "change", "change_rate_percent", "formula", "sample_rows", "cells",
        }
        # JSON field names, confidence scores and addresses are NOT cell values.
        return [
            _claim_values(item)
            for key, item in value.items()
            if key in source_fields
        ]
    if isinstance(value, list):
        return [_claim_values(item) for item in value]
    return value
