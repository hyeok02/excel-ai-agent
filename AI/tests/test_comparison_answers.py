import asyncio
from types import SimpleNamespace

from app.agent.execution import AgentStepStatus
from app.agent.execution.models import AgentExecutionEvidence
from app.agent.query.answer_validation import validate_answer
from app.agent.query.comparison_answers import validated_comparison_answer
from app.agent.query.index import WorkbookDataIndex
from app.agent.query.models import QuestionAnswerDraft, QuestionAnswerStatus
from app.agent.query.service import WorkbookQuestionService
from app.services.provenance import EvidenceKind
from app.services.workbook_parsing.models import WorkbookSummary

QUESTION = "제일 많이 감소한 부서는 어디고 몇 명 감소했어?"
EXPECTED = (
    "2023년 9월 1일부터 2025년 6월 1일까지 가장 많이 감소한 부서는 "
    "서비스(Services)입니다. 1,277명에서 1,081명으로 196명 감소했습니다."
)


def test_verified_comparison_replaces_unsupported_model_answer() -> None:
    draft = QuestionAnswerDraft(answer="모르겠습니다.", evidence=[], confidence=0.1)

    answer = validate_answer(QUESTION, draft, _execution(), False)

    assert answer.status is QuestionAnswerStatus.ANSWERED
    assert answer.answer == EXPECTED


def test_service_skips_model_when_verified_comparison_can_answer() -> None:
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
    assert answer.answer == EXPECTED


def test_comparison_values_must_match_cited_cells() -> None:
    execution = _execution()
    metric = execution.steps[0].result.data["time_series_comparison"]["ranked_changes"][0]
    metric["end_value"] = 999
    metric["change"] = -278

    assert validated_comparison_answer(QUESTION, execution, False) is None


def test_comparison_requires_original_header_evidence() -> None:
    execution = _execution()
    comparison = execution.steps[0].result.data["time_series_comparison"]
    comparison["ranked_changes"][0].pop("header_references")

    assert validated_comparison_answer(QUESTION, execution, False) is None


def _execution():
    values = {
        "W106": "Department", "W107": "Services",
        "E115": "2023-09-01", "E108": "2025-06-01",
        "W115": 1277, "W108": 1081,
    }
    evidence = [
        AgentExecutionEvidence(
            kind=EvidenceKind.CELL, sheet_name="Metrics", reference=reference,
            description="Department > Services", value=value,
        )
        for reference, value in values.items()
    ]
    comparison = {
        "start_date": "2023-09-01", "end_date": "2025-06-01",
        "start_reference": "Metrics!E115", "end_reference": "Metrics!E108",
        "metric_group": "department", "change_direction": "decrease",
        "ranked_changes": [{
            "header": "Services", "start_value": 1277, "end_value": 1081,
            "change": -196.0,
            "header_references": ["Metrics!W106", "Metrics!W107"],
            "start_reference": "Metrics!W115", "end_reference": "Metrics!W108",
        }],
    }
    result = SimpleNamespace(
        evidence=evidence,
        data={"calculations": [], "verified_insights": [],
              "time_series_comparison": comparison},
    )
    step = SimpleNamespace(
        status=AgentStepStatus.SUCCEEDED, result=result,
        tool_name="search_workbook_data",
    )
    return SimpleNamespace(steps=[step])


class _FailingGenerator:
    async def generate(self, *_args, **_kwargs):
        raise AssertionError("검증된 비교 답변은 LLM을 호출하면 안 됩니다.")


class _StubExecutor:
    def __init__(self, execution) -> None:
        self.execution = execution

    def execute(self, *_args, **_kwargs):
        return self.execution
