import asyncio
from types import SimpleNamespace

from app.agent.execution import AgentStepStatus
from app.agent.execution.models import AgentExecutionEvidence
from app.agent.query.index import WorkbookDataIndex
from app.agent.query.models import QuestionAnswerStatus
from app.agent.query.router import build_question_plan
from app.agent.query.service import WorkbookQuestionService
from app.agent.query.structure_answers import validated_structure_answer
from app.services.provenance import EvidenceKind
from app.services.workbook_parsing.models import WorkbookSummary

QUESTION = "이 파일은 어떤 시트로 구성돼 있어?"
EXPECTED = (
    "이 파일은 시트 3개로 구성되어 있습니다. "
    "분석 결과가 정리된 시트는 Summary입니다. "
    "값을 계산하는 시트는 Intermediate입니다. "
    "사용 방법을 설명하는 시트는 Instructions입니다. "
    "숨김 시트 1개는 분석에서 제외했습니다."
)


def test_structure_question_plans_semantic_structure_tool() -> None:
    plan = build_question_plan(QUESTION)

    assert "inspect_semantic_structure" in [step.tool_name for step in plan.steps]


def test_sheet_composition_is_answered_without_the_model() -> None:
    answer = validated_structure_answer(QUESTION, _execution(), False)

    assert answer is not None
    assert answer.status is QuestionAnswerStatus.ANSWERED
    assert answer.answer == EXPECTED
    assert answer.evidence


def test_service_skips_model_for_sheet_composition_question() -> None:
    service = WorkbookQuestionService(
        _FailingGenerator(), SimpleNamespace(), _StubExecutor(_execution())
    )

    answer = asyncio.run(
        service.answer(
            QUESTION,
            WorkbookSummary("book.xlsx", 0, []),
            WorkbookDataIndex("book.xlsx", (), 0, False),
        )
    )

    assert answer.answer == EXPECTED


def test_other_questions_are_left_to_the_normal_pipeline() -> None:
    assert validated_structure_answer("매출이 얼마야?", _execution(), False) is None


def test_structure_answer_requires_matching_cell_evidence() -> None:
    execution = _execution()
    execution.steps[0].result.evidence.clear()

    assert validated_structure_answer(QUESTION, execution, False) is None


def _execution():
    evidence = [
        AgentExecutionEvidence(
            kind=EvidenceKind.CELL, sheet_name=name, reference="B2",
            description=f"{name} 역할 판정 근거", value=name,
        )
        for name in ("Summary", "Intermediate", "Instructions")
    ]
    data = {
        "sheets": [
            {"name": "Summary", "role": "output", "importance_score": 90},
            {"name": "Intermediate", "role": "calculation", "importance_score": 40},
            {"name": "Instructions", "role": "documentation", "importance_score": 10},
        ],
        "excluded_sheets": [{"name": "__hidden", "state": "veryHidden"}],
    }
    step = SimpleNamespace(
        status=AgentStepStatus.SUCCEEDED,
        result=SimpleNamespace(evidence=evidence, data=data),
        tool_name="inspect_semantic_structure",
    )
    return SimpleNamespace(steps=[step])


class _FailingGenerator:
    async def generate(self, *_args, **_kwargs):
        raise AssertionError("검증된 시트 구성 답변은 LLM을 호출하면 안 됩니다.")


class _StubExecutor:
    def __init__(self, execution) -> None:
        self.execution = execution

    def execute(self, *_args, **_kwargs):
        return self.execution
