import asyncio
from types import SimpleNamespace

from app.agent.execution import AgentStepStatus
from app.agent.execution.models import AgentExecutionEvidence
from app.agent.query.index import WorkbookDataIndex
from app.agent.query.intent_models import QuestionIntent
from app.agent.query.models import QuestionAnswerStatus
from app.agent.query.service import WorkbookQuestionService
from app.agent.query.verified_insight_answers import validated_verified_insight_answer
from app.services.provenance import EvidenceKind
from app.services.workbook_parsing.models import WorkbookSummary


QUESTION = "부서 등 항목별 전체 직원 수 변화 알려줘"
DEPARTMENT_FACT = (
    "연구개발은 1,145명에서 1,816명으로 증가했고, "
    "인사부는 337명에서 437명으로 증가했습니다."
)


def test_reuses_the_matching_verified_fact_instead_of_calling_the_model() -> None:
    service = WorkbookQuestionService(
        _FailingGenerator(), SimpleNamespace(), _StubExecutor(_execution())
    )

    answer = asyncio.run(
        service.answer(
            QUESTION,
            WorkbookSummary("headcount.xlsm", 0, []),
            WorkbookDataIndex("headcount.xlsm", (), 0, False),
        )
    )

    assert answer.status is QuestionAnswerStatus.ANSWERED
    assert answer.answer == DEPARTMENT_FACT
    assert {item.reference for item in answer.evidence} == {"B1", "B2", "C1", "C2"}


def test_does_not_reuse_a_change_fact_for_an_unverified_average_request() -> None:
    answer = validated_verified_insight_answer(
        "연구개발 평균 인원은?", _execution(), False
    )

    assert answer is None


def test_model_target_can_match_a_cross_language_question() -> None:
    answer = validated_verified_insight_answer(
        "R&D 인원이 얼마나 늘었어?",
        _execution(),
        False,
        QuestionIntent(False, "comparison", ("Research & Development",), True),
    )

    assert answer is not None
    assert answer.answer == DEPARTMENT_FACT


def test_r_and_d_abbreviation_matches_without_a_classifier() -> None:
    answer = validated_verified_insight_answer(
        "R&D 직원 수 변화 알려줘", _execution(), False
    )

    assert answer is not None and answer.answer == DEPARTMENT_FACT


def test_unknown_team_is_not_replaced_by_the_overall_employee_fact() -> None:
    assert validated_verified_insight_answer(
        "IT 직원 수 변화 알려줘", _execution(), False
    ) is None


def _execution():
    evidence = [
        _evidence("A1", 3955, "전체 직원 시작"),
        _evidence("A2", 5417, "전체 직원 종료"),
        _evidence("B1", 1145, "연구개발 시작"),
        _evidence("B2", 1816, "연구개발 종료"),
        _evidence("C1", 337, "인사부 시작"),
        _evidence("C2", 437, "인사부 종료"),
    ]
    insights = [
        {
            "title": "전체 직원 수 변화",
            "topic": "Total Employees",
            "category": "change",
            "fact": "전체 직원 수는 3,955명에서 5,417명으로 증가했습니다.",
            "support_references": ["인원!A1:A2"],
            "confidence": 1.0,
        },
        {
            "title": "부서 등 항목별 전체 직원 수 변화",
            "topic": "Department > Research & Development",
            "category": "change",
            "fact": DEPARTMENT_FACT,
            "support_references": ["인원!B1:B2", "인원!C1:C2"],
            "confidence": 1.0,
        },
    ]
    result = SimpleNamespace(
        evidence=evidence,
        data={
            "verified_insights": insights,
            "workbook_summary_query": False,
            "index_truncated": False,
        },
    )
    step = SimpleNamespace(
        status=AgentStepStatus.SUCCEEDED,
        result=result,
        tool_name="search_workbook_data",
    )
    return SimpleNamespace(steps=[step])


def _evidence(reference, value, description):
    return AgentExecutionEvidence(
        kind=EvidenceKind.CELL,
        sheet_name="인원",
        reference=reference,
        description=description,
        value=value,
    )


class _FailingGenerator:
    async def generate(self, *_args, **_kwargs):
        raise AssertionError("검증된 인사이트 질문은 LLM을 호출하면 안 됩니다.")


class _StubExecutor:
    def __init__(self, execution) -> None:
        self.execution = execution

    def execute(self, *_args, **_kwargs):
        return self.execution
