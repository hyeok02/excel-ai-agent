from io import BytesIO
import json

from fastapi.testclient import TestClient
from openpyxl import Workbook
import pytest

from app.agent.query.tabular_catalog import build_query_tables
from app.api import workbook_questions as endpoint
from app.main import app
from app.services.workbook_parser import parse_workbook
from tests.support.clarification_fixtures import NeverModel, QueryClassifier


@pytest.fixture
def api(monkeypatch):
    book = Workbook()
    book.active.title = "Metrics"
    for row in [["Record", "Revenue (USD)", "Revenue (EUR)"], ["One", 10, 100], ["Two", 20, 200]]:
        book.active.append(row)
    stream = BytesIO()
    book.save(stream)
    content = stream.getvalue()
    summary = parse_workbook("metrics.xlsx", content)
    classifier = QueryClassifier(build_query_tables(summary)[0], "C")
    monkeypatch.setattr(endpoint, "_intent_classifier", classifier)
    app.dependency_overrides[endpoint.get_question_answer_generator] = lambda: NeverModel()
    app.dependency_overrides[endpoint.get_question_context_resolver] = lambda: NeverModel()
    with TestClient(app) as client:
        yield client, content, classifier
    app.dependency_overrides.clear()


def post(api, question, context=None):
    client, content, _ = api
    data = {"question": question}
    if context is not None:
        data["context"] = json.dumps(context)
    return client.post("/api/v1/workbooks/questions", data=data, files={
        "file": ("metrics.xlsx", content, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"),
    })


def test_api_exposes_options_and_accepts_only_current_canonical_selection(api):
    first = post(api, "Revenue 합계는?")
    assert first.status_code == 200
    choices = first.json()["clarification_options"]
    assert len(choices) == 2
    option = choices[1]
    assert set(option) == {"id", "label", "scope", "details", "question"}
    result = post(api, option["question"], {"selection": {
        "source_question": first.json()["question"], "option_id": option["id"],
    }})
    assert result.status_code == 200
    assert result.json()["resolved_question"] == option["question"]
    assert "300" in result.json()["answer"]
    assert result.json()["verification"]["level"] == "request_checked"


@pytest.mark.parametrize("selection", [
    {"source_question": "Revenue 합계는?", "option_id": "bad"},
    {"source_question": "x", "option_id": "a" * 64},
    {"source_question": "x" * 1001, "option_id": "a" * 64},
    {"source_question": "Revenue 합계는?", "option_id": "A" * 64},
    {"source_question": "Revenue 합계는?", "option_id": "a" * 64, "value": 999},
    {"source_question": "Revenue 합계는?", "option_id": "a" * 64, "evidence": ["Metrics!C2"]},
])
def test_api_rejects_invalid_selection_schema_without_classifying(api, selection):
    response = post(api, "Revenue 합계는?", {"selection": selection})
    assert response.status_code == 422
    assert api[2].questions == []


def test_api_rejects_forged_valid_shape_identifier_without_classifying(api):
    response = post(api, "Revenue 합계는?", {"selection": {
        "source_question": "Revenue 합계는?", "option_id": "0" * 64,
    }})
    assert response.status_code == 200
    assert response.json()["status"] == "insufficient_evidence"
    assert response.json()["verification"]["level"] == "unverified"
    assert response.json()["evidence"] == []
    assert api[2].questions == []
