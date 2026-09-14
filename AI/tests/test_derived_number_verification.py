from types import SimpleNamespace

from app.agent.execution import AgentStepStatus
from app.agent.execution.models import AgentExecutionEvidence
from app.agent.query.answer_validation import validate_answer
from app.agent.query.models import QuestionAnswerDraft, QuestionAnswerStatus
from app.services.provenance import EvidenceKind

QUESTION = "눈에 띄는 차이와 그 근거는?"
CITED = ["Headcount!E115", "Headcount!E108", "Headcount!F115", "Headcount!F108"]


def _answer(text: str):
    draft = QuestionAnswerDraft(answer=text, evidence=CITED, confidence=0.8)
    return validate_answer(QUESTION, draft, _execution(), False)


def test_difference_between_cited_values_is_accepted() -> None:
    answer = _answer("전체 직원 수는 6,101명에서 5,417명으로 684명 감소했습니다.")

    assert answer.status is QuestionAnswerStatus.ANSWERED
    assert "684" in answer.answer


def test_percent_change_between_cited_values_is_accepted() -> None:
    answer = _answer("전체 직원 수는 6,101명에서 5,417명으로 11.21% 감소했습니다.")

    assert answer.status is QuestionAnswerStatus.ANSWERED


def test_wrong_difference_is_still_rejected() -> None:
    answer = _answer("전체 직원 수는 6,101명에서 5,417명으로 700명 감소했습니다.")

    assert answer.status is QuestionAnswerStatus.INSUFFICIENT_EVIDENCE


def test_wrong_percent_change_is_still_rejected() -> None:
    answer = _answer("전체 직원 수는 6,101명에서 5,417명으로 25% 감소했습니다.")

    assert answer.status is QuestionAnswerStatus.INSUFFICIENT_EVIDENCE


def test_difference_without_its_operands_is_rejected() -> None:
    answer = _answer("전체 직원 수가 684명 감소했습니다.")

    assert answer.status is QuestionAnswerStatus.INSUFFICIENT_EVIDENCE


def test_date_cell_is_not_treated_as_a_row_label() -> None:
    answer = _answer(
        "전체 직원 수는 2023년 9월 1일 6,101명에서 "
        "2025년 6월 1일 5,417명으로 684명 감소했습니다."
    )

    assert answer.status is QuestionAnswerStatus.ANSWERED


def _execution():
    values = {
        "E115": "2023-09-01T00:00:00", "E108": "2025-06-01T00:00:00",
        "F115": 6101, "F108": 5417,
    }
    evidence = [
        AgentExecutionEvidence(
            kind=EvidenceKind.CELL, sheet_name="Headcount", reference=reference,
            description="Total Employees", value=value,
        )
        for reference, value in values.items()
    ]
    result = SimpleNamespace(
        evidence=evidence, data={"calculations": [], "verified_insights": []}
    )
    step = SimpleNamespace(
        status=AgentStepStatus.SUCCEEDED, result=result,
        tool_name="search_workbook_data",
    )
    return SimpleNamespace(steps=[step])
