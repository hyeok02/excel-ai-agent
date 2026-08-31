import asyncio
from datetime import UTC, datetime

import pytest

from app.agent import (
    AgentExecution,
    AgentExecutionPlan,
    AgentExecutionStatus,
    AgentPlanStep,
    AgentStepExecution,
    AgentStepStatus,
)
from app.agent.execution.models import (
    AgentExecutionEvidence,
    AgentToolExecutionResult,
)
from app.agent.insights import LangChainAgentInsightGenerator, build_execution_insight_context
from app.services.insights.models import InsightGenerationError
from app.services.provenance import EvidenceKind


def execution(succeeded: bool = True) -> AgentExecution:
    plan = AgentExecutionPlan(
        user_intent="외부 참조 위험을 알려줘",
        objective="위험 수식과 영향을 확인합니다.",
        user_value="원본 전체를 보지 않고 우선 검토 셀을 찾습니다.",
        expected_deliverable="근거와 신뢰도가 있는 위험 인사이트",
        steps=[
            AgentPlanStep(
                id="step_1",
                title="수식 위험 확인",
                tool_name="assess_formula_risks",
                purpose="외부 참조 수식을 찾습니다.",
                rationale="갱신되지 않는 값을 우선 확인해야 합니다.",
                expected_output="외부 참조와 영향 범위",
                evidence_required=["수식 셀과 원문"],
            )
        ],
        success_criteria=["위험에 셀 근거가 있어야 합니다."],
    )
    now = datetime.now(UTC)
    result = None
    if succeeded:
        result = AgentToolExecutionResult(
            summary="외부 참조 1건을 확인했습니다.",
            data={"external_reference_count": 1},
            evidence=[
                AgentExecutionEvidence(
                    kind=EvidenceKind.FORMULA,
                    sheet_name="Sales",
                    reference="D2",
                    description="외부 파일 참조 수식",
                    formula="='[Budget.xlsx]Plan'!C3",
                )
            ],
        )
    step = AgentStepExecution(
        step_id="step_1",
        title="수식 위험 확인",
        tool_name="assess_formula_risks",
        purpose="외부 참조 수식을 찾습니다.",
        expected_output="외부 참조와 영향 범위",
        status=AgentStepStatus.SUCCEEDED if succeeded else AgentStepStatus.FAILED,
        started_at=now,
        completed_at=now,
        result=result,
    )
    return AgentExecution(
        execution_id="execution-1",
        status=AgentExecutionStatus.SUCCEEDED if succeeded else AgentExecutionStatus.FAILED,
        summary="1단계 성공" if succeeded else "1단계 실패",
        started_at=now,
        completed_at=now,
        succeeded_step_count=1 if succeeded else 0,
        failed_step_count=0 if succeeded else 1,
        skipped_step_count=0,
        plan=plan,
        steps=[step],
    )


class StubModel:
    def __init__(self) -> None:
        self.messages = []

    async def ainvoke(self, messages):
        self.messages = messages
        return {
            "overview": "외부 참조 수식 1건은 우선 검토가 필요합니다.",
            "insights": [
                {
                    "title": "외부 참조 확인",
                    "fact": "Sales!D2가 Budget.xlsx를 참조합니다.",
                    "cause": "수식 원문에 외부 파일 참조가 있습니다.",
                    "impact": "외부 파일 갱신 상태에 따라 결과가 달라질 수 있습니다.",
                    "category": "risk",
                    "severity": "warning",
                    "evidence": ["Sales!D2"],
                    "recommendation": "외부 파일 갱신 상태를 확인하세요.",
                    "confidence": 0.97,
                }
            ],
            "limitations": [],
        }


def test_generates_insights_from_tool_results_and_evidence(monkeypatch) -> None:
    model = StubModel()
    generator = LangChainAgentInsightGenerator("key", "model", 10)
    monkeypatch.setattr(generator, "_build_model", lambda: model)

    report = asyncio.run(generator.generate(execution()))

    assert report.insights[0].confidence == 0.97
    assert '"reference":"D2"' in model.messages[1].content
    assert "원본 Excel" in model.messages[0].content


def test_rejects_execution_without_successful_tool_results() -> None:
    generator = LangChainAgentInsightGenerator("key", "model", 10)

    with pytest.raises(InsightGenerationError, match="성공한 Agent Tool"):
        asyncio.run(generator.generate(execution(False)))


def test_bounds_large_tool_data_before_llm_prompt() -> None:
    value = execution()
    value.steps[0].result.data = {"large": "x" * 20_000}

    context = build_execution_insight_context(value)

    assert context["steps"][0]["data_truncated"] is True
    assert len(context["steps"][0]["data_excerpt"]) == 12_000
