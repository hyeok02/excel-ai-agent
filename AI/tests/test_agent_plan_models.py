import pytest
from pydantic import ValidationError

from app.agent import AgentExecutionPlan, AgentPlanStep, create_default_tool_registry
from app.agent.planning import PlanGenerationError, ensure_executable_plan


def _plan(step: AgentPlanStep) -> AgentExecutionPlan:
    return AgentExecutionPlan(
        user_intent="수식 오류가 의사결정에 미치는 영향을 알려줘",
        objective="위험 수식과 연결 범위를 근거와 함께 확인합니다.",
        user_value="원본 시트를 일일이 따라가지 않고 우선 검토할 수식을 압축합니다.",
        expected_deliverable="위험 수식, 영향 범위와 근거 위치를 포함한 검토 순서",
        steps=[step],
        success_criteria=["모든 판단에 셀 또는 수식 근거가 연결되어야 합니다."],
    )


def test_rejects_forward_or_unknown_step_dependencies() -> None:
    with pytest.raises(ValidationError, match="앞서 정의"):
        AgentExecutionPlan(
            user_intent="구조를 분석해줘",
            objective="워크북 구조를 확인합니다.",
            user_value="핵심 시트를 빠르게 찾습니다.",
            expected_deliverable="검토할 시트와 영역 목록",
            steps=[
                AgentPlanStep(
                    id="step_1",
                    title="구조 확인",
                    tool_name="inspect_semantic_structure",
                    purpose="핵심 시트와 영역을 찾습니다.",
                    rationale="분석 범위를 먼저 정해야 합니다.",
                    expected_output="업무 시트와 제외 시트 구분",
                    evidence_required=["시트 역할 판단 근거"],
                    depends_on=["step_2"],
                )
            ],
            success_criteria=["분석 범위가 정리되어야 합니다."],
        )


def test_rejects_unregistered_tool_and_invalid_arguments() -> None:
    tools = create_default_tool_registry().list_metadata()
    unknown = _plan(
        AgentPlanStep(
            id="step_1",
            title="알 수 없는 분석",
            tool_name="invented_tool",
            purpose="등록되지 않은 기능을 시도합니다.",
            rationale="검증 실패를 확인하기 위한 단계입니다.",
            expected_output="실행할 수 없는 결과",
            evidence_required=["근거"],
        )
    )
    with pytest.raises(PlanGenerationError, match="등록되지 않은"):
        ensure_executable_plan(unknown, tools)

    invalid = unknown.model_copy(
        update={
            "steps": [
                unknown.steps[0].model_copy(
                    update={
                        "tool_name": "assess_formula_risks",
                        "arguments": {"finding_limit": 101},
                    }
                )
            ]
        }
    )
    with pytest.raises(PlanGenerationError, match="너무 큽니다"):
        ensure_executable_plan(invalid, tools)
