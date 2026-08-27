import json
from pathlib import Path

import pytest

from app.services.provenance import (
    AnalysisEvidence,
    AnalysisMethod,
    EvidenceKind,
    Provenance,
    evidence_from_reference,
)


def test_splits_qualified_cell_reference() -> None:
    evidence = evidence_from_reference(
        "기본 시트",
        "'매출 현황'!B2:C4",
        "헤더와 값 분포가 확인된 범위",
    )

    assert evidence.kind is EvidenceKind.RANGE
    assert evidence.sheet_name == "매출 현황"
    assert evidence.reference == "B2:C4"


def test_formula_evidence_keeps_original_formula_and_value() -> None:
    evidence = evidence_from_reference(
        "요약",
        "D2",
        "워크북에서 직접 추출한 원본 수식",
        value=30,
        formula="=SUM(B2:C2)",
    )

    assert evidence.kind is EvidenceKind.FORMULA
    assert evidence.formula == "=SUM(B2:C2)"
    assert evidence.value == 30


def test_rejects_provenance_without_evidence() -> None:
    with pytest.raises(ValueError, match="하나 이상의 근거"):
        Provenance("test_analyzer", AnalysisMethod.RULE_BASED, 0.8, ())


def test_rejects_formula_evidence_without_formula() -> None:
    with pytest.raises(ValueError, match="원본 수식"):
        AnalysisEvidence(
            EvidenceKind.FORMULA,
            "요약",
            "D2",
            "수식 근거",
        )


def test_shared_contract_matches_python_enums() -> None:
    contract_path = Path(__file__).parents[2] / "contracts" / (
        "analysis-provenance.schema.json"
    )
    contract = json.loads(contract_path.read_text(encoding="utf-8"))

    assert contract["properties"]["method"]["enum"] == [
        method.value for method in AnalysisMethod
    ]
    assert contract["$defs"]["evidence"]["properties"]["kind"]["enum"] == [
        kind.value for kind in EvidenceKind
    ]
