"""Real upload route uses fresh chronology without any live model calls."""
from fastapi.testclient import TestClient
import pytest

from app.api import workbook_questions as endpoint
from app.main import app
from tests.support.large_workbook_fixtures import (
    ForbiddenExternalCall, NoGeneratedAnswer, offline, parsed, workbook,
)


class NoClassifier:
    async def classify(self, *args):
        raise ForbiddenExternalCall("A source trend must not need model classification")


@pytest.fixture
def client(monkeypatch):
    saved = dict(app.dependency_overrides)
    monkeypatch.setattr(endpoint, "_intent_classifier", NoClassifier())
    app.dependency_overrides[endpoint.get_question_answer_generator] = lambda: NoGeneratedAnswer()
    app.dependency_overrides[endpoint.get_question_context_resolver] = lambda: None
    try:
        with TestClient(app) as value:
            yield value
    finally:
        app.dependency_overrides.clear()
        app.dependency_overrides.update(saved)


def upload(client, scale, question):
    _, _, content = parsed(workbook({"Records": [
        ["Date", "Total Employees"], ["2024-04-01", 13 * scale],
        ["2024-03-01", 12 * scale], ["2024-02-01", 15 * scale], ["2024-01-01", 10 * scale],
    ]}))
    response = client.post("/api/v1/workbooks/questions", data={"question": question},
                           files={"file": ("same-name.xlsx", content)})
    assert response.status_code == 200, response.text
    return response.json()


def test_upload_route_reads_new_file_values_and_intermediate_reversal(client):
    for scale in (1, 10, 1):
        answer = upload(client, scale, "전체 직원 수의 기간별 추이를 설명해줘")
        assert answer["status"] == "answered", answer
        assert answer["verification"]["level"] == "request_checked"
        assert f"{15 * scale}명 → {12 * scale}명" in answer["answer"]
        assert f"{12 * scale}명 → {13 * scale}명" in answer["answer"]
        assert "하락 뒤 반등" in answer["answer"]
        assert answer["selected_tools"] == ["chronological_trend"]


def test_upload_route_certifies_computed_growth_not_the_underlying_raw_series(client):
    answer = upload(client, 1, "전체 직원 수 증가율의 기간별 추이를 설명해줘")
    assert answer["status"] == "answered", answer
    assert answer["verification"]["level"] == "request_checked"
    assert "derived_trend" in answer["selected_tools"]
    assert "(현재값 - 이전 기준값) / 이전 기준값 × 100" in answer["answer"]
    assert "2024-02-01: 50%" in answer["answer"] and "2024-03-01: -20%" in answer["answer"]
    assert "2024-04-01: 8.33%" in answer["answer"] and "50% → 8.33%" in answer["answer"]
    assert "3개 시점" in answer["answer"] and "10명 → 13명" not in answer["answer"]
    assert {("B2", 13), ("B3", 12), ("B4", 15), ("B5", 10)} <= {
        (cell["reference"], cell["value"]) for cell in answer["evidence"]}
