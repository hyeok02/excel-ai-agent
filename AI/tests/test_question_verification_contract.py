"""A response being available or citing a cell is not a correctness guarantee."""
from types import SimpleNamespace

import pytest

from app.agent.execution import AgentStepStatus
from app.agent.execution.models import AgentExecutionEvidence
from app.agent.query.answer_validation import validate_answer
from app.agent.query.comparison_evidence import present_comparison_evidence
from app.agent.query.models import (
    QuestionAnswer, QuestionAnswerDraft, QuestionAnswerStatus,
    QuestionVerificationLevel,
)
from app.services.provenance import EvidenceKind


def test_answered_status_does_not_imply_request_verification():
    answer = QuestionAnswer(
        question="조건에 해당하는 건수는?", answer="10건", status="answered",
        confidence=1, selected_tools=[], evidence=[], limitations=[],
    )

    assert answer.verification.level == QuestionVerificationLevel.UNVERIFIED
    assert answer.verification.checks == []


def test_generated_supported_value_is_source_checked_not_scope_verified():
    evidence = _evidence("C8", 12, "수량")
    execution = _execution([evidence])
    draft = QuestionAnswerDraft(answer="수량은 12개입니다.", evidence=["Moved!C8"], confidence=1)

    answer = validate_answer("수량은?", draft, execution, False)

    assert answer.status == QuestionAnswerStatus.ANSWERED
    assert answer.verification.level == QuestionVerificationLevel.SOURCE_CHECKED
    assert "cited_cells" in answer.verification.checks


def test_failed_claim_never_gets_source_or_request_verification():
    draft = QuestionAnswerDraft(answer="수량은 99개입니다.", evidence=["Moved!C8"], confidence=1)

    answer = validate_answer("수량은?", draft, _execution([_evidence("C8", 12, "수량")]), False)

    assert answer.status == QuestionAnswerStatus.INSUFFICIENT_EVIDENCE
    assert answer.verification.level == QuestionVerificationLevel.UNVERIFIED


@pytest.mark.parametrize("sheet,address", [("Log", "J11"), ("Renamed", "R53")])
def test_evidence_label_reports_actual_value_not_neighbor_description(sheet, address):
    evidence = AgentExecutionEvidence(
        kind=EvidenceKind.FORMULA, sheet_name=sheet, reference=address,
        description="Unrelated Neighbor Corp announcement", value="Target and Partner agreement",
        formula="=EXTERNAL_DATA()",
    )

    rendered = present_comparison_evidence(evidence)

    assert rendered.label == "원본 값: Target and Partner agreement"
    assert "Neighbor" not in rendered.label
    assert rendered.formula == "=EXTERNAL_DATA()"


def _evidence(reference, value, description):
    return AgentExecutionEvidence(kind=EvidenceKind.CELL, sheet_name="Moved", reference=reference,
                                  value=value, description=description)


def _execution(evidence):
    result = SimpleNamespace(evidence=evidence, data={})
    return SimpleNamespace(steps=[SimpleNamespace(result=result, tool_name="search_workbook_data",
                                                status=AgentStepStatus.SUCCEEDED)])
