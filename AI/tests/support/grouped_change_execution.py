from types import SimpleNamespace

from app.agent.execution import AgentStepStatus
from app.agent.execution.models import AgentExecutionEvidence
from app.services.provenance import EvidenceKind

QUESTION = "부서 등 항목별 전체 직원 수 변화를 시작 값과 마지막 값 기준으로 비교해줘"


def grouped_execution(group="department"):
    values = {
        "A2": "2020-09-01", "A3": "2025-06-01",
        "B1": "Research & Development", "B2": 1145, "B3": 1816,
        "C1": "Services", "C2": 1000, "C3": 900,
    }
    comparison = {
        "sheet_name": "인원", "metric_group": group,
        "start_date": "2020-09-01", "end_date": "2025-06-01",
        "start_reference": "인원!A2", "end_reference": "인원!A3",
        "metrics": [_metric(values, column) for column in "BC"],
    }
    evidence = [
        AgentExecutionEvidence(
            kind=EvidenceKind.CELL, sheet_name="인원", reference=reference,
            description="원본 값", value=value,
        )
        for reference, value in values.items()
    ]
    result = SimpleNamespace(
        evidence=evidence,
        data={"time_series_comparison": comparison, "index_truncated": False},
    )
    step = SimpleNamespace(
        status=AgentStepStatus.SUCCEEDED, result=result,
        tool_name="search_workbook_data",
    )
    return SimpleNamespace(steps=[step])


def _metric(values, column):
    return {
        "header": values[f"{column}1"],
        "header_references": [f"인원!{column}1"],
        "start_value": values[f"{column}2"], "end_value": values[f"{column}3"],
        "change": values[f"{column}3"] - values[f"{column}2"],
        "start_reference": f"인원!{column}2", "end_reference": f"인원!{column}3",
    }


class FailingGenerator:
    async def generate(self, *_args, **_kwargs):
        raise AssertionError("verified grouped changes must not call the model")


class StubExecutor:
    def __init__(self, execution):
        self.execution = execution

    def execute(self, *_args, **_kwargs):
        return self.execution
