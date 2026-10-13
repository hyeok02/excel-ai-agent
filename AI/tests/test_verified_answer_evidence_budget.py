"""검증된 답변이 근거로 드는 셀은 상한 때문에 잘리면 안 된다."""
from app.agent.query.verified_evidence import merge_evidence
from app.services.provenance import AnalysisEvidence, EvidenceKind


def _evidence(reference: str) -> AnalysisEvidence:
    return AnalysisEvidence(
        kind=EvidenceKind.CELL, sheet_name="시트", reference=reference,
        description="셀", value=1,
    )


def test_priority_evidence_survives_the_limit() -> None:
    # 근거 21개 중 하나가 상한에 잘려 요약 답변이 통째로 버려진 적이 있다.
    priority = [_evidence(f"A{row}") for row in range(1, 121)]
    ordinary = [_evidence(f"B{row}") for row in range(1, 121)]

    merged = merge_evidence(priority, ordinary, 100)
    references = {item.reference for item in merged}

    assert {item.reference for item in priority} <= references


def test_ordinary_evidence_still_respects_the_limit() -> None:
    priority = [_evidence(f"A{row}") for row in range(1, 11)]
    ordinary = [_evidence(f"B{row}") for row in range(1, 500)]

    assert len(merge_evidence(priority, ordinary, 100)) == 100
