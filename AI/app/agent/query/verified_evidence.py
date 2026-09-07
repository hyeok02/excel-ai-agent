from dataclasses import replace

from app.agent.query.index import IndexedRow
from app.agent.query.references import matching_references, normalize_reference
from app.services.provenance import AnalysisEvidence

MODEL_EVIDENCE_WINDOW = 120
QUERY_EVIDENCE_RESERVE = 40


def priority_evidence(
    rows: tuple[IndexedRow, ...], verified: dict[str, object]
) -> list[AnalysisEvidence]:
    references = verified.get("priority_references", [])
    if not isinstance(references, list):
        return []
    ordered = [
        normalized
        for value in references
        if isinstance(value, str)
        if (normalized := normalize_reference(value))
    ]
    cells = {
        normalized: cell
        for row in rows
        for cell in row.cells
        if (normalized := normalize_reference(cell.reference))
    }
    descriptions = _descriptions(verified)
    result = []
    available = set(cells)
    for requested in dict.fromkeys(ordered):
        matches = matching_references(requested, available)
        for reference in cells:
            if reference not in matches:
                continue
            evidence = cells[reference].evidence()
            if description := descriptions.get(reference):
                format_hint = (
                    f" (Excel 표시 형식: {cells[reference].number_format})"
                    if "%" in cells[reference].number_format
                    else ""
                )
                evidence = replace(evidence, description=f"{description}{format_hint}")
            result.append(evidence)
    return result


def merge_evidence(
    priority: list[AnalysisEvidence],
    ordinary: list[AnalysisEvidence],
    limit: int,
) -> tuple[AnalysisEvidence, ...]:
    priority = _unique_evidence(priority)
    ordinary = _unique_evidence(ordinary)
    priority_head_size = MODEL_EVIDENCE_WINDOW - QUERY_EVIDENCE_RESERVE
    priority_head = priority[:priority_head_size]
    visible = {_evidence_key(item) for item in priority_head}
    query_head = [item for item in ordinary if _evidence_key(item) not in visible]
    candidates = [
        *priority_head,
        *query_head[:QUERY_EVIDENCE_RESERVE],
        *priority[priority_head_size:],
        *ordinary,
    ]
    return tuple(_unique_evidence(candidates)[:limit])


def _unique_evidence(items: list[AnalysisEvidence]) -> list[AnalysisEvidence]:
    merged = {}
    for item in items:
        if (key := _evidence_key(item)) and key not in merged:
            merged[key] = item
    return list(merged.values())


def _evidence_key(item: AnalysisEvidence) -> str | None:
    return normalize_reference(f"{item.sheet_name}!{item.reference}")


def range_count_calculations(
    rows: tuple[IndexedRow, ...], verified: dict[str, object]
) -> list[dict[str, object]]:
    specs = verified.get("count_specs", [])
    if not isinstance(specs, list):
        return []
    cells = {
        normalized: cell
        for row in rows
        for cell in row.cells
        if (normalized := normalize_reference(cell.reference))
    }
    available = set(cells)
    calculations = []
    for spec in specs:
        if not isinstance(spec, dict):
            continue
        reference = normalize_reference(spec.get("range"))
        matches = matching_references(reference, available) if reference else set()
        ordered = [key for key in cells if key in matches]
        valid = [
            key
            for key in ordered
            if isinstance(cells[key].value, (int, float))
            and not isinstance(cells[key].value, bool)
        ]
        label = str(spec.get("label") or "비교거래")
        if len(ordered) == spec.get("peer_count"):
            calculations.append(_count(label, ordered, cells, "전체 비교거래 건수"))
        if len(valid) == spec.get("valid_count"):
            calculations.append(_count(label, valid, cells, "값이 있는 비교거래 건수"))
    return calculations


def _count(label, references, cells, suffix):
    return {
        "operation": "count",
        "operand_references": references,
        "operand_values": [cells[reference].value for reference in references],
        "result": len(references),
        "unit": "count",
        "label": f"{label} {suffix}",
    }


def _descriptions(verified: dict[str, object]) -> dict[str, str]:
    values = verified.get("reference_descriptions", {})
    if not isinstance(values, dict):
        return {}
    return {
        normalized: description
        for reference, description in values.items()
        if isinstance(reference, str) and isinstance(description, str)
        if (normalized := normalize_reference(reference))
    }
