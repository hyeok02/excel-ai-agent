"""확인 못 한 수치 하나가 답변 전체를 지우지 않는지."""
from types import SimpleNamespace

from app.agent.execution import AgentStepStatus
from app.agent.execution.models import AgentExecutionEvidence
from app.agent.query.answer_validation import validate_answer
from app.agent.query.models import QuestionAnswerDraft, QuestionAnswerStatus
from app.services.provenance import EvidenceKind

QUESTION = "제일 많은 인원이 감소한 부서는 어디야?"


def _evidence(reference, value, description):
    return AgentExecutionEvidence(
        kind=EvidenceKind.CELL, sheet_name="인원", reference=reference,
        description=description, value=value,
    )


def _execution(evidence):
    step = SimpleNamespace(
        status=AgentStepStatus.SUCCEEDED,
        result=SimpleNamespace(evidence=evidence, data={}),
        tool_name="search_workbook_data",
    )
    return SimpleNamespace(steps=[step])


EVIDENCE = [
    _evidence("N107", "Research & Development", "부서명"),
    _evidence("N115", 1959, "2023-09 인원"),
    _evidence("N108", 1816, "2025-06 인원"),
]


def test_keeps_the_grounded_sentence_when_one_number_is_unverified() -> None:
    # 143은 어느 셀에도 없는 뺄셈 결과다. 예전에는 이 한 수 때문에 앞 문장까지
    # 묻혀 사용자가 아무것도 보지 못했다.
    draft = QuestionAnswerDraft(
        answer="Research & Development가 가장 많이 줄었습니다. 143명 감소했습니다.",
        evidence=["인원!N107", "인원!N108", "인원!N115"],
        confidence=0.9,
    )

    answer = validate_answer(QUESTION, draft, _execution(EVIDENCE), False)

    assert answer.status is not QuestionAnswerStatus.INSUFFICIENT_EVIDENCE
    assert "Research & Development" in answer.answer
    assert "143" not in answer.answer
    assert any("빼고 보여줍니다" in item for item in answer.limitations)


def test_keeps_the_whole_answer_when_both_endpoints_are_stated() -> None:
    draft = QuestionAnswerDraft(
        answer=(
            "Research & Development가 1,959명에서 1,816명으로 143명 감소해 "
            "가장 많이 줄었습니다."
        ),
        evidence=["인원!N107", "인원!N108", "인원!N115"],
        confidence=0.9,
    )

    answer = validate_answer(QUESTION, draft, _execution(EVIDENCE), False)

    assert answer.status is not QuestionAnswerStatus.INSUFFICIENT_EVIDENCE
    assert "143" in answer.answer
    assert not any("빼고 보여줍니다" in item for item in answer.limitations)
