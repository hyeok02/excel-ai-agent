import json
from pathlib import Path

import pytest

from app.api.workbooks import SemanticClassificationResponse
from app.services.semantic_models import (
    SemanticClassification,
    SemanticReason,
    SemanticRole,
)


CONTRACT_PATH = (
    Path(__file__).parents[2] / "contracts" / "semantic-classification.schema.json"
)


def test_semantic_roles_match_shared_contract() -> None:
    contract = json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))

    assert [role.value for role in SemanticRole] == contract["$defs"][
        "semanticRole"
    ]["enum"]


def test_serializes_semantic_classification_with_wire_values() -> None:
    classification = SemanticClassification(
        role=SemanticRole.TITLE,
        confidence=0.92,
        reasons=(
            SemanticReason(
                code="merged_title",
                message="병합된 첫 행의 굵은 텍스트",
                evidence_cells=("매출!A1",),
            ),
        ),
    )

    response = SemanticClassificationResponse.model_validate(classification)

    assert response.model_dump(mode="json") == {
        "role": "title",
        "confidence": 0.92,
        "reasons": [
            {
                "code": "merged_title",
                "message": "병합된 첫 행의 굵은 텍스트",
                "evidence_cells": ["매출!A1"],
            }
        ],
    }


@pytest.mark.parametrize("confidence", [-0.01, 1.01])
def test_rejects_confidence_outside_unit_interval(confidence: float) -> None:
    with pytest.raises(ValueError, match="신뢰도"):
        SemanticClassification(role=SemanticRole.DATA, confidence=confidence)


def test_rejects_duplicate_reason_evidence_cells() -> None:
    with pytest.raises(ValueError, match="중복"):
        SemanticReason(
            code="duplicate",
            message="중복 근거",
            evidence_cells=("Sheet1!A1", "Sheet1!A1"),
        )


def test_rejects_unknown_role_value() -> None:
    with pytest.raises(ValueError, match="정의되지 않은"):
        SemanticClassification(role="other", confidence=0.5)  # type: ignore[arg-type]
