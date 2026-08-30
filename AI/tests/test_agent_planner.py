import asyncio

from app.agent import AgentExecutionPlan, LangChainAgentPlanner, create_default_tool_registry
from app.agent.planning import build_planning_context
from app.agent.planning.drafts import AgentExecutionPlanDraft
from app.services.workbook_parsing.models import WorkbookSummary


def _result() -> dict[str, object]:
    return {
        "schema_version": "1.0",
        "user_intent": "모델이 바꾼 문장",
        "objective": "업무 시트와 계산 영역을 구분합니다.",
        "user_value": "원본 전체를 탐색하지 않고 검토할 핵심 영역을 찾습니다.",
        "expected_deliverable": "시트 역할과 근거 범위를 포함한 분석 순서",
        "steps": [
            {
                "id": "step_1",
                "title": "의미 구조 확인",
                "tool_name": "inspect_semantic_structure",
                "arguments": [],
                "purpose": "업무 시트와 제외 영역을 구분합니다.",
                "rationale": "잘못된 영역을 분석하면 결론이 왜곡될 수 있습니다.",
                "expected_output": "검토 대상 시트와 영역의 우선순위",
                "evidence_required": ["시트 역할 판단 근거", "포함·제외 사유"],
                "depends_on": [],
            }
        ],
        "success_criteria": ["결과에 시트와 영역 근거가 포함되어야 합니다."],
        "assumptions": [],
        "limitations": ["계획 단계에서는 분석 결과를 확정하지 않습니다."],
    }


class StubStructuredModel:
    def __init__(self) -> None:
        self.messages = []

    async def ainvoke(self, messages):
        self.messages = messages
        return _result()


def test_creates_validated_plan_and_preserves_original_intent(monkeypatch) -> None:
    model = StubStructuredModel()
    planner = LangChainAgentPlanner("key", "model", 10)
    monkeypatch.setattr(planner, "_build_model", lambda: model)
    tools = create_default_tool_registry().list_metadata()
    summary = WorkbookSummary(filename="매출.xlsx", sheet_count=0, sheets=[])

    plan = asyncio.run(
        planner.create_plan("  핵심 시트를 알려줘  ", summary, tools)
    )

    assert isinstance(plan, AgentExecutionPlan)
    assert plan.user_intent == "핵심 시트를 알려줘"
    assert plan.steps[0].tool_name == "inspect_semantic_structure"
    assert "원본 Excel" in model.messages[0].content
    assert '"filename":"매출.xlsx"' in model.messages[1].content


def test_planning_context_exposes_only_registered_tools_and_workbook_overview() -> None:
    summary = WorkbookSummary(filename="finance.xlsx", sheet_count=0, sheets=[])
    tools = create_default_tool_registry().list_metadata()

    context = build_planning_context(summary, tools)

    assert context["workbook"]["filename"] == "finance.xlsx"
    assert [tool["name"] for tool in context["available_tools"]] == [
        "inspect_semantic_structure",
        "trace_formula_dependencies",
        "detect_circular_references",
        "assess_formula_risks",
    ]


def test_llm_plan_schema_uses_closed_argument_items() -> None:
    schema = AgentExecutionPlanDraft.model_json_schema()
    step_schema = schema["$defs"]["AgentPlanStepDraft"]
    argument_schema = schema["$defs"]["AgentPlanArgumentDraft"]

    assert step_schema["properties"]["arguments"]["type"] == "array"
    assert step_schema["additionalProperties"] is False
    assert argument_schema["additionalProperties"] is False
