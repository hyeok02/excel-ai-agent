import asyncio
from types import SimpleNamespace

from app.agent.execution import AgentStepStatus
from app.agent.execution.models import AgentExecutionEvidence
from app.agent.query.index import WorkbookDataIndex
from app.agent.query.models import QuestionAnswerStatus
from app.agent.query.service import WorkbookQuestionService
from app.agent.tools.workbook_metric_snapshots import build_metric_snapshot
from app.services.provenance import EvidenceKind
from app.services.workbook_parsing.models import WorkbookSummary

QUESTION = "부서 등 항목별 전체 직원 수 알려줘"


def test_service_answers_grouped_latest_values_without_the_model() -> None:
    execution = _execution()
    service = WorkbookQuestionService(
        _FailingGenerator(), SimpleNamespace(), _StubExecutor(execution)
    )

    answer = asyncio.run(service.answer(
        QUESTION,
        WorkbookSummary("headcount.xlsm", 0, []),
        WorkbookDataIndex("headcount.xlsm", (), 0, False),
    ))

    assert answer.status is QuestionAnswerStatus.ANSWERED
    assert "2025년 6월 1일 기준 부서별 직원 수" in answer.answer
    assert "연구개발(Research & Development) 1,816명" in answer.answer
    assert "Human Resources 437명" in answer.answer
    assert {item.reference for item in answer.evidence} == {
        "A2", "B1", "B2", "C1", "C2",
    }


def test_month_with_multiple_observations_is_not_reduced_to_its_first_value() -> None:
    comparison = {
        "sheet_name": "Sales", "start_date": "2025-03-01",
        "end_date": "2025-03-31", "observation_count": 2,
        "start_reference": "Sales!A2", "end_reference": "Sales!A32",
        "metrics": [{
            "header": "Sales", "start_value": 100, "end_value": 200,
            "change": 100, "header_references": ["Sales!B1"],
            "start_reference": "Sales!B2", "end_reference": "Sales!B32",
        }],
    }

    assert build_metric_snapshot(comparison, "Sales in March 2025") is None


def test_month_with_one_observation_keeps_the_exact_value() -> None:
    comparison = {
        "sheet_name": "Sales", "start_date": "2025-03-31",
        "end_date": "2025-03-31", "observation_count": 1,
        "start_reference": "Sales!A2", "end_reference": "Sales!A2",
        "metrics": [{
            "header": "Sales", "start_value": 100, "end_value": 100,
            "change": 0, "header_references": ["Sales!B1"],
            "start_reference": "Sales!B2", "end_reference": "Sales!B2",
        }],
    }

    found = build_metric_snapshot(comparison, "Sales in March 2025")

    assert found is not None and found["metrics"][0]["value"] == 100


def _execution():
    values = {
        "A2": "2025-06-01", "B1": "Research & Development", "B2": 1816,
        "C1": "Human Resources", "C2": 437,
    }
    evidence = [
        AgentExecutionEvidence(
            kind=EvidenceKind.CELL, sheet_name="인원", reference=reference,
            description="원본 값", value=value,
        )
        for reference, value in values.items()
    ]
    snapshot = {
        "group": "부서", "end_date": "2025-06-01",
        "period_reference": "인원!A2",
        "metrics": [
            _metric("Research & Development", "B", 1816),
            _metric("Human Resources", "C", 437),
        ],
    }
    result = SimpleNamespace(
        evidence=evidence,
        data={"metric_snapshot": snapshot, "index_truncated": False},
    )
    step = SimpleNamespace(
        status=AgentStepStatus.SUCCEEDED, result=result,
        tool_name="search_workbook_data",
    )
    return SimpleNamespace(steps=[step])


def _metric(header: str, column: str, value: int) -> dict:
    return {
        "header": header, "header_references": [f"인원!{column}1"],
        "value": value, "value_reference": f"인원!{column}2",
    }


class _FailingGenerator:
    async def generate(self, *_args, **_kwargs):
        raise AssertionError("latest snapshot must not call the model")


class _StubExecutor:
    def __init__(self, execution) -> None:
        self.execution = execution

    def execute(self, *_args, **_kwargs):
        return self.execution
