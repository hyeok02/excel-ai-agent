from collections.abc import Iterable
from typing import Protocol

from app.services.provenance.models import (
    AnalysisEvidence,
    AnalysisMethod,
    EvidenceKind,
    EvidenceValue,
    Provenance,
)


class ReasonLike(Protocol):
    message: str
    evidence_cells: tuple[str, ...]


def evidence_from_reference(
    sheet_name: str,
    reference: str,
    description: str,
    *,
    value: EvidenceValue = None,
    formula: str | None = None,
) -> AnalysisEvidence:
    resolved_sheet, resolved_reference = _split_reference(sheet_name, reference)
    kind = EvidenceKind.FORMULA if formula else _reference_kind(resolved_reference)
    return AnalysisEvidence(
        kind=kind,
        sheet_name=resolved_sheet,
        reference=resolved_reference,
        description=description,
        value=value,
        formula=formula,
    )


def evidence_from_reasons(
    sheet_name: str,
    reasons: Iterable[ReasonLike],
) -> tuple[AnalysisEvidence, ...]:
    evidence: list[AnalysisEvidence] = []
    seen: set[tuple[str, str]] = set()
    for reason in reasons:
        for reference in reason.evidence_cells:
            item = evidence_from_reference(sheet_name, reference, reason.message)
            key = (item.sheet_name, item.reference or "")
            if key not in seen:
                evidence.append(item)
                seen.add(key)
    return tuple(evidence)


def sheet_evidence(sheet_name: str, description: str) -> AnalysisEvidence:
    return AnalysisEvidence(
        kind=EvidenceKind.SHEET,
        sheet_name=sheet_name,
        reference=None,
        description=description,
    )


def build_provenance(
    analyzer: str,
    confidence: float | None,
    evidence: Iterable[AnalysisEvidence],
    method: AnalysisMethod = AnalysisMethod.RULE_BASED,
) -> Provenance:
    return Provenance(analyzer, method, confidence, tuple(evidence))


def _split_reference(default_sheet: str, reference: str) -> tuple[str, str]:
    if "!" not in reference:
        return default_sheet, reference
    sheet_name, cell_reference = reference.rsplit("!", 1)
    return sheet_name.strip("'"), cell_reference


def _reference_kind(reference: str) -> EvidenceKind:
    return EvidenceKind.RANGE if ":" in reference else EvidenceKind.CELL
