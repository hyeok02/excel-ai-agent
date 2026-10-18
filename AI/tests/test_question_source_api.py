from fastapi.testclient import TestClient
import pytest

from app.api import workbook_questions as endpoint
from app.main import app
from tests.support.large_workbook_fixtures import (
    FixedClassifier, NoGeneratedAnswer, offline, parsed, plan_for, tiny_caps, workbook,
)


@pytest.fixture
def client():
    saved = dict(app.dependency_overrides)
    app.dependency_overrides[endpoint.get_question_answer_generator] = lambda: NoGeneratedAnswer()
    app.dependency_overrides[endpoint.get_question_context_resolver] = lambda: None
    with TestClient(app) as client:
        yield client
    app.dependency_overrides.clear()
    app.dependency_overrides.update(saved)


def source(scale=1):
    return parsed(workbook({"Records": [["Record", "Amount"],
                  *[[f"Item{n}", n * scale] for n in range(1, 9)]]}))


def post(client, content, question):
    response = client.post("/api/v1/workbooks/questions", data={"question": question},
                           files={"file": ("same-name.xlsx", content)})
    assert response.status_code == 200, response.text
    return response.json()


def test_api_attaches_fresh_source_for_each_uploaded_file(client, tiny_caps, monkeypatch):
    summary, _, first = source()
    _, _, second = source(10)
    monkeypatch.setattr(endpoint, "_intent_classifier", FixedClassifier(plan_for(summary)))
    for content, expected in [(first, "합계 36"), (second, "합계 360"), (first, "합계 36")]:
        answer = post(client, content, "Records 시트 Amount 합계는?")
        assert expected in answer["answer"]
        assert answer["verification"]["level"] == "request_checked"
        assert "full_source_scan" in answer["verification"]["checks"]


def test_api_tail_address_never_invokes_classifier_or_answer_model(client, tiny_caps, monkeypatch):
    class NoClassifier:
        async def classify(self, *args):
            raise BaseException("Direct source lookup must not invoke a classifier")

    _, _, content = source()
    monkeypatch.setattr(endpoint, "_intent_classifier", NoClassifier())
    answer = post(client, content, "Records!B9 값은?")
    assert answer["answer"] == "Records!B9: 8"
    assert answer["verification"]["level"] == "request_checked"
    assert answer["selected_tools"] == ["read_original_cells"]
