from types import SimpleNamespace

from app.agent.execution import AgentStepStatus
from app.agent.execution.models import AgentExecutionEvidence
from app.agent.query.answer_validation import validate_answer
from app.agent.query.models import QuestionAnswerDraft, QuestionAnswerStatus
from app.services.provenance import EvidenceKind


def test_validation_never_returns_a_prefix_of_a_source_label() -> None:
    evidence = [
        AgentExecutionEvidence(
            kind=EvidenceKind.CELL, sheet_name="Sheet", reference=reference,
            description=description, value=value,
        )
        for reference, description, value in (
            ("A1", "항목", "North. Annex"), ("B1", "건수", 3),
        )
    ]
    execution = SimpleNamespace(steps=[SimpleNamespace(
        status=AgentStepStatus.SUCCEEDED, tool_name="search_workbook_data",
        result=SimpleNamespace(evidence=evidence, data={}),
    )])
    draft = QuestionAnswerDraft(
        answer="항목별로 보면 - 'North. Annex'의 건수는 999입니다.",
        evidence=["Sheet!A1:B1"], confidence=0.9,
    )

    answer = validate_answer("항목별 건수를 알려줘", draft, execution, False)

    assert answer.status is QuestionAnswerStatus.INSUFFICIENT_EVIDENCE
    assert answer.confidence == 0
    assert "North." not in answer.answer


def test_independent_verified_fact_survives_an_unverified_label_value() -> None:
    evidence = [
        AgentExecutionEvidence(
            kind=EvidenceKind.CELL, sheet_name="Sheet", reference=reference,
            description=description, value=value,
        )
        for reference, description, value in (
            ("A1", "항목", "North. Annex"), ("B1", "건수", 3),
        )
    ]
    execution = SimpleNamespace(steps=[SimpleNamespace(
        status=AgentStepStatus.SUCCEEDED, tool_name="search_workbook_data",
        result=SimpleNamespace(evidence=evidence, data={}),
    )])
    draft = QuestionAnswerDraft(
        answer="'North. Annex'의 건수는 3입니다. 추가 건수는 999입니다.",
        evidence=["Sheet!A1:B1"], confidence=0.9,
    )

    answer = validate_answer("항목별 건수를 알려줘", draft, execution, False)

    assert answer.status is QuestionAnswerStatus.LIMITED
    assert answer.answer == "'North. Annex'의 건수는 3입니다."
