from fastapi.testclient import TestClient

from app.api.agent_insights import get_agent_insight_generator
from app.main import app
from app.services.insights.models import WorkbookInsight, WorkbookInsightReport
from tests.test_agent_insight_generator import execution

client = TestClient(app)


class StubAgentInsightGenerator:
    async def generate(self, agent_execution) -> WorkbookInsightReport:
        return WorkbookInsightReport(
            overview="외부 참조 수식을 확인했습니다.",
            insights=[
                WorkbookInsight(
                    title="외부 참조 확인",
                    fact="Sales!D2가 외부 파일을 참조합니다.",
                    cause="수식에 외부 통합문서 경로가 포함되어 있습니다.",
                    impact="외부 파일 상태에 따라 계산 결과가 달라질 수 있습니다.",
                    category="risk",
                    severity="warning",
                    evidence=["Sales!D2"],
                    recommendation="외부 파일 연결을 확인하세요.",
                    confidence=0.96,
                )
            ],
            limitations=[],
        )


def test_returns_structured_insights_from_agent_execution() -> None:
    app.dependency_overrides[get_agent_insight_generator] = StubAgentInsightGenerator
    try:
        response = client.post(
            "/api/v1/agent/insights",
            json=execution().model_dump(mode="json"),
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    insight = response.json()["insights"][0]
    assert insight["fact"].startswith("Sales!D2")
    assert insight["cause"]
    assert insight["impact"]
    assert insight["evidence"] == ["Sales!D2"]
    assert insight["confidence"] == 0.96
