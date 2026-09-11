import asyncio
from types import SimpleNamespace

from app.agent.execution import AgentStepStatus
from app.agent.execution.models import AgentExecutionEvidence
from app.agent.query.index import WorkbookDataIndex
from app.agent.query.models import QuestionAnswerStatus
from app.agent.query.service import WorkbookQuestionService
from app.agent.query.workbook_summary_answers import (
    validated_workbook_summary_answer,
)
from app.services.provenance import EvidenceKind
from app.services.workbook_parsing.models import WorkbookSummary

QUESTION = "이 파일은 무엇을 비교하고 있어?"
OVERVIEW = "전체 직원 수와 부서별 직원 수의 기간별 변화를 비교합니다."


def test_service_skips_model_for_verified_workbook_summary() -> None:
    service = WorkbookQuestionService(
        _FailingGenerator(), SimpleNamespace(), _StubExecutor(_execution())
    )

    answer = asyncio.run(
        service.answer(
            QUESTION,
            WorkbookSummary("headcount.xlsx", 0, []),
            WorkbookDataIndex("headcount.xlsx", (), 0, False),
        )
    )

    assert answer.status is QuestionAnswerStatus.ANSWERED
    assert answer.answer == OVERVIEW
    assert {item.reference for item in answer.evidence} == {"A1", "B2"}


def test_verified_summary_requires_every_support_reference() -> None:
    execution = _execution()
    execution.steps[0].result.evidence.pop()

    assert validated_workbook_summary_answer(QUESTION, execution, False) is None


def test_verified_summary_keeps_answer_when_scope_is_truncated() -> None:
    answer = validated_workbook_summary_answer(QUESTION, _execution(), True)

    assert answer is not None
    assert answer.status is QuestionAnswerStatus.LIMITED
    assert answer.answer == OVERVIEW
    assert "일부 관련 셀" in answer.limitations[0]


def _execution():
    evidence = [
        AgentExecutionEvidence(
            kind=EvidenceKind.CELL,
            sheet_name="Metrics",
            reference=reference,
            description="검증된 요약 근거",
            value=value,
        )
        for reference, value in (("A1", "Total Employees"), ("B2", 5417))
    ]
    data = {
        "workbook_summary_query": True,
        "verified_overview": OVERVIEW,
        "verified_insights": [
            {"support_references": ["Metrics!A1", "Metrics!B2"]}
        ],
        "index_truncated": False,
    }
    result = SimpleNamespace(evidence=evidence, data=data)
    step = SimpleNamespace(
        status=AgentStepStatus.SUCCEEDED,
        result=result,
        tool_name="search_workbook_data",
    )
    return SimpleNamespace(steps=[step])


class _FailingGenerator:
    async def generate(self, *_args, **_kwargs):
        raise AssertionError("검증된 요약 답변은 LLM을 호출하면 안 됩니다.")


class _StubExecutor:
    def __init__(self, execution) -> None:
        self.execution = execution

    def execute(self, *_args, **_kwargs):
        return self.execution
