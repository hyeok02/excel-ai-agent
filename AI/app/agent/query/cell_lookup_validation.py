"""Validate both the requested operation and the three actual lookup cell values."""
from app.agent.query.comparison_evidence import comparison_values_match
from app.agent.tools.workbook_lookup_guards import (
    lookup_header_matches,
    scalar_lookup_question,
)


def valid_cell_lookup(question: str, found: dict, available: dict) -> bool:
    header = str(found.get("header") or "")
    label = str(found.get("label") or "")
    if not lookup_header_matches(question, header):
        return False
    if not scalar_lookup_question(question, header, label):
        return False
    checks = tuple(
        (found.get(f"{key}_reference"), found.get(key))
        for key in ("header", "label", "value")
    )
    return all(reference for reference, _ in checks) and comparison_values_match(
        checks, available
    )
