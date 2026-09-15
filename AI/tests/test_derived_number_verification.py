from types import SimpleNamespace

from app.agent.execution import AgentStepStatus
from app.agent.execution.models import AgentExecutionEvidence
from app.agent.query.answer_validation import validate_answer
from app.agent.query.models import QuestionAnswerDraft, QuestionAnswerStatus
from app.services.provenance import EvidenceKind

QUESTION = "눈에 띄는 차이와 그 근거는?"
CITED = [
    "Headcount!E115", "Headcount!E108",
    "Headcount!F115", "Headcount!F108",
    "Headcount!G115", "Headcount!G108",
]


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


def test_only_the_stated_base_counts_as_a_change_rate() -> None:
    """12.63%는 기준을 뒤집은 값, 88.79%와 112.63%는 비중이라 감소율이 아니다."""
    for wrong in ("12.63", "88.79", "112.63"):
        answer = _answer(f"전체 직원 수는 6,101명에서 5,417명으로 {wrong}% 감소했습니다.")

        assert answer.status is QuestionAnswerStatus.INSUFFICIENT_EVIDENCE


def test_difference_without_its_operands_is_rejected() -> None:
    answer = _answer("전체 직원 수가 684명 감소했습니다.")

    assert answer.status is QuestionAnswerStatus.INSUFFICIENT_EVIDENCE


def test_stated_increase_on_decreasing_values_is_rejected() -> None:
    """줄어든 값을 두고 증가라고 쓰면 수치가 맞아도 통과시키지 않는다."""
    for wrong in ("684명", "11.21%"):
        answer = _answer(f"전체 직원 수는 6,101명에서 5,417명으로 {wrong} 증가했습니다.")

        assert answer.status is QuestionAnswerStatus.INSUFFICIENT_EVIDENCE


def test_real_increase_is_accepted() -> None:
    """실제로 늘어난 방향으로 쓰면 그대로 통과한다."""
    answer = _answer("전체 직원 수는 5,417명에서 6,101명으로 684명 증가했습니다.")

    assert answer.status is QuestionAnswerStatus.ANSWERED


def test_direction_is_checked_per_clause() -> None:
    """한 문장 안에서도 절마다 따로 본다."""
    answer = _answer(
        "전체 직원 수는 6,101명에서 5,417명으로 684명 감소했고, "
        "일반관리는 1,018명에서 904명으로 114명 증가했습니다."
    )

    assert answer.status is QuestionAnswerStatus.INSUFFICIENT_EVIDENCE


def test_ratio_between_cited_values_is_accepted() -> None:
    """증감을 말하지 않는 문장에서는 비중도 원본으로 재현해 인정한다."""
    answer = _answer("904명은 5,417명의 16.69%입니다.")

    assert answer.status is QuestionAnswerStatus.ANSWERED


def test_ratio_binds_its_numerator_and_denominator() -> None:
    """"A는 B의 P%"는 A÷B×100 한 값만 인정한다."""
    for wrong in ("112.63", "12.63"):
        answer = _answer(f"5,417명은 6,101명의 {wrong}%입니다.")

        assert answer.status is QuestionAnswerStatus.INSUFFICIENT_EVIDENCE


def test_one_clause_does_not_vouch_for_another() -> None:
    """앞 절에서 만들어진 근거로 뒤 절의 주장을 통과시키지 않는다."""
    answer = _answer(
        "5,417명은 6,101명의 88.79%이고, "
        "일반관리는 1,018명에서 904명으로 88.79% 감소했습니다."
    )

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
        "G115": 1018, "G108": 904,
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
