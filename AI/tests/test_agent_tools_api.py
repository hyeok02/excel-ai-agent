from fastapi.testclient import TestClient

from app.main import app

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
