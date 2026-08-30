from fastapi.testclient import TestClient
from pytest import MonkeyPatch

from app.agent import AgentExecutionPlan, AgentPlanStep
from app.api.agent_tools import get_agent_planner
from app.main import app
from tests.support.workbook_api_fixtures import create_workbook_file, upload

client = TestClient(app)


def test_lists_registered_agent_tools_for_future_planner() -> None:
    response = client.get("/api/v1/agent/tools")

    assert response.status_code == 200
    assert [tool["name"] for tool in response.json()] == [
        "inspect_semantic_structure",
        "trace_formula_dependencies",
        "detect_circular_references",
        "assess_formula_risks",
    ]
    assert all(tool["capabilities"] for tool in response.json())


class StubAgentPlanner:
    def __init__(self) -> None:
        self.intent = ""
        self.filename = ""
        self.tool_names: list[str] = []

    async def create_plan(self, intent, summary, tools) -> AgentExecutionPlan:
        self.intent = intent
        self.filename = summary.filename
        self.tool_names = [tool.name for tool in tools]
        return AgentExecutionPlan(
            user_intent=intent,
            objective="위험 수식과 영향을 근거로 확인합니다.",
            user_value="검토해야 할 수식과 관련 시트를 원본 탐색 전에 좁힙니다.",
            expected_deliverable="수식 위험과 근거를 확인하는 실행 순서",
            steps=[
                AgentPlanStep(
                    id="step_1",
                    title="수식 위험 확인",
                    tool_name="assess_formula_risks",
                    purpose="오류와 경고 수식을 찾습니다.",
                    rationale="우선 검토할 계산 오류를 좁혀야 합니다.",
                    expected_output="심각도별 수식 위험 목록",
                    evidence_required=["위험 수식 셀과 수식 원문"],
                )
            ],
            success_criteria=["위험마다 원본 셀 근거가 있어야 합니다."],
        )


def test_creates_structured_agent_plan_without_executing_tools() -> None:
    planner = StubAgentPlanner()
    app.dependency_overrides[get_agent_planner] = lambda: planner
    try:
        response = client.post(
            "/api/v1/agent/plans",
            data={"intent": "깨진 수식이 있는지 알려줘"},
            files=upload("sales.xlsx", create_workbook_file()),
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert planner.intent == "깨진 수식이 있는지 알려줘"
    assert planner.filename == "sales.xlsx"
    assert len(planner.tool_names) == 4
    assert response.json()["steps"][0]["tool_name"] == "assess_formula_risks"
    assert "원본 탐색 전에" in response.json()["user_value"]


def test_plan_api_returns_service_unavailable_without_api_key(
    monkeypatch: MonkeyPatch,
) -> None:
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.setattr("app.agent.planning.planner.load_dotenv", lambda _: False)
    response = client.post(
        "/api/v1/agent/plans",
        data={"intent": "핵심 시트를 알려줘"},
        files=upload("sales.xlsx", create_workbook_file()),
    )
    assert response.status_code == 503
    assert "OPENAI_API_KEY" in response.json()["detail"]
