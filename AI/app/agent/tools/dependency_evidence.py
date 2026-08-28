from collections.abc import Iterable

from app.services.dependencies.models import DependencyNode
from app.services.provenance import AnalysisEvidence, EvidenceKind


def dependency_evidence(
    nodes: Iterable[DependencyNode],
) -> tuple[AnalysisEvidence, ...]:
    evidence: list[AnalysisEvidence] = []
    seen: set[str] = set()
    for node in nodes:
        if not node.sheet or not node.cell or not node.formula or node.id in seen:
            continue
        seen.add(node.id)
        evidence.append(
            AnalysisEvidence(
                kind=EvidenceKind.FORMULA,
                sheet_name=node.sheet,
                reference=node.cell,
                description="수식 참조 그래프에서 확인한 계산 셀",
                formula=node.formula,
            )
        )
    return tuple(evidence)
