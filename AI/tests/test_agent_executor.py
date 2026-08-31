from app.agent import (
    AgentExecutionPlan,
    AgentPlanStep,
    AgentToolContext,
    AgentToolMetadata,
    AgentToolRegistry,
    AgentToolResult,
    AgentToolExecutor,
    StepFailurePolicy,
    ToolCategory,
)
from app.services.provenance import AnalysisEvidence, EvidenceKind
from app.services.workbook_parsing.models import WorkbookSummary


class SuccessTool:
    metadata = AgentToolMetadata(
        name="success_tool",
        description="테스트 성공 도구",
        category=ToolCategory.SEMANTIC,
        capabilities=("성공 결과 반환",),
    )

    def execute(self, context, arguments=None):
        return AgentToolResult(
            tool_name=self.metadata.name,
            summary="근거가 있는 결과를 확인했습니다.",
            data={"filename": context.workbook.filename},
            evidence=(
                AnalysisEvidence(
                    kind=EvidenceKind.CELL,
                    sheet_name="매출",
                    reference="A1",
                    description="테스트 근거 셀",
                ),
            ),
        )


class FailureTool:
    metadata = AgentToolMetadata(
        name="failure_tool",
        description="테스트 실패 도구",
        category=ToolCategory.VALIDATION,
        capabilities=("실패 처리 검증",),
    )

    def execute(self, context, arguments=None):
        raise RuntimeError("외부에 노출하면 안 되는 내부 오류")


def _step(step_id, tool_name, *, depends_on=None, on_failure="stop"):
    return AgentPlanStep(
        id=step_id,
        title=f"{step_id} 실행",
        tool_name=tool_name,
        purpose="워크북 분석 결과를 확인합니다.",
        rationale="사용자 판단에 필요한 근거를 확보합니다.",
        expected_output="근거가 연결된 분석 결과",
        evidence_required=["원본 셀 근거"],
        depends_on=depends_on or [],
        on_failure=on_failure,
    )


def _plan(steps):
    return AgentExecutionPlan(
        user_intent="Excel 위험을 확인해줘",
        objective="도구 실행 결과와 근거를 확인합니다.",
        user_value="원본 전체를 보지 않고 검토 대상을 좁힙니다.",
        expected_deliverable="성공과 실패 상태가 포함된 분석 결과",
        steps=steps,
        success_criteria=["성공한 단계에 원본 근거가 있어야 합니다."],
    )


def _execute(steps):
    registry = AgentToolRegistry((SuccessTool(), FailureTool()))
    context = AgentToolContext(WorkbookSummary("sales.xlsx", 0, []))
    return AgentToolExecutor().execute(_plan(steps), context, registry)


def test_executes_tool_and_preserves_evidence() -> None:
    execution = _execute([_step("step_1", "success_tool")])

    assert execution.status == "succeeded"
    assert execution.steps[0].result.data == {"filename": "sales.xlsx"}
    assert execution.steps[0].result.evidence[0].reference == "A1"


def test_stop_policy_fails_and_skips_remaining_steps() -> None:
    execution = _execute(
        [_step("step_1", "failure_tool"), _step("step_2", "success_tool")]
    )

    assert execution.status == "failed"
    assert [step.status for step in execution.steps] == ["failed", "skipped"]
    assert execution.steps[0].error.code == "TOOL_EXECUTION_FAILED"
    assert "내부 오류" not in execution.steps[0].error.message


def test_continue_policy_runs_independent_steps_and_skips_dependents() -> None:
    execution = _execute(
        [
            _step("step_1", "failure_tool", on_failure=StepFailurePolicy.CONTINUE),
            _step("step_2", "success_tool"),
            _step("step_3", "success_tool", depends_on=["step_1"]),
        ]
    )

    assert execution.status == "partial"
    assert [step.status for step in execution.steps] == [
        "failed",
        "succeeded",
        "skipped",
    ]
    assert execution.steps[2].error.code == "DEPENDENCY_NOT_SUCCEEDED"
