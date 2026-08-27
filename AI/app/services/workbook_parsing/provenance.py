from dataclasses import replace

from app.services.analysis_inclusion import AnalysisInclusion
from app.services.provenance import (
    build_provenance,
    evidence_from_reasons,
    sheet_evidence,
)
from app.services.sheet_classifier import SheetClassification


def with_inclusion_provenance(
    sheet_name: str,
    inclusion: AnalysisInclusion,
) -> AnalysisInclusion:
    return replace(
        inclusion,
        provenance=build_provenance(
            "worksheet_inclusion_policy",
            1.0,
            (sheet_evidence(sheet_name, inclusion.reason),),
        ),
    )


def with_classification_provenance(
    sheet_name: str,
    classification: SheetClassification,
) -> SheetClassification:
    evidence = evidence_from_reasons(sheet_name, classification.reasons)
    if not evidence:
        evidence = (
            sheet_evidence(
                sheet_name,
                f"{classification.role.value} 역할과 중요도 산정 대상 시트",
            ),
        )
    return replace(
        classification,
        provenance=build_provenance(
            "sheet_role_classifier",
            classification.confidence,
            evidence,
        ),
    )
