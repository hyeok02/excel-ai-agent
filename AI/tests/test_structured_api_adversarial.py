"""Multipart upload API emits only independently checked compound results."""
from fastapi.testclient import TestClient
import pytest

from app.api import workbook_questions as endpoint
from app.main import app
from tests.support.replanning_adversarial import NoGeneration, Planner, intent, offline
from tests.support.structured_adversarial import compound, plan, source
from tests.test_replanning_failures_adversarial import ProviderError


@pytest.fixture
def api(monkeypatch):
    summary, _, content = source()
    planner = Planner(None, None)
    monkeypatch.setattr(endpoint, "_intent_classifier", planner)
    saved = dict(app.dependency_overrides)
    app.dependency_overrides[endpoint.get_question_answer_generator] = lambda: NoGeneration()
    app.dependency_overrides[endpoint.get_question_context_resolver] = lambda: None
    try:
        with TestClient(app) as client:
            yield client, summary, content, planner
    finally:
        app.dependency_overrides.clear()
        app.dependency_overrides.update(saved)


def post(api, question):
    client, _, content, _ = api
    return client.post("/api/v1/workbooks/questions", data={"question": question}, files={
        "file": ("generated-source.xlsx", content, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")})


def test_api_complete_boolean_compound_has_separate_evidence_and_coverage(api):
    _, summary, _, planner = api
    prefix = "(Region = 'North' OR Region = 'South') AND NOT Status = 'Closed'"
    texts = ["Amount 합계", "Amount 평균"]
    planner.first = compound(texts, [plan(summary, condition=prefix),
                                   plan(summary, condition=prefix, statistic="average")], prefix)
    response = post(api, prefix + ": " + "; ".join(texts))
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["status"] == "answered" and body["verification"]["level"] == "request_checked"
    assert "compound_parts_2" in body["verification"]["checks"]
    assert {entry["label"].split(" · ")[0] for entry in body["evidence"]} == {"문항 1", "문항 2"}
    assert "합계 50" in body["answer"] and "평균 25" in body["answer"]
    assert len(planner.questions) == 1 and planner.repairs == []


@pytest.mark.parametrize("failure", ["bad_plan", "dependent", "uncovered_part"])
def test_api_partial_or_uncovered_request_never_has_whole_verified_badge(api, failure):
    _, summary, _, planner = api
    second = plan(summary, statistic="average")
    texts = ["Amount 합계", "그중 상위 3개" if failure == "dependent" else "Amount 평균"]
    if failure == "bad_plan":
        second = second.model_copy(update={"column_ids": ["E"]})
    planner.first = compound(texts, [plan(summary), second])
    question = "; ".join(texts) + ("; Costs 합계" if failure == "uncovered_part" else "")
    response = post(api, question)
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["status"] != "answered" and body["verification"]["level"] != "request_checked"
    assert "compound_request_coverage" not in body["verification"]["checks"]
    if failure != "uncovered_part":
        assert body["status"] == "limited" and "합계 100" in body["answer"]
        assert all(item["label"].startswith("문항 1 · ") for item in body["evidence"])
    assert planner.repairs == []


@pytest.mark.parametrize("quota", [False, True])
def test_api_replan_quota_or_corrected_plan_has_explicit_safe_result(api, quota):
    _, summary, _, planner = api
    correct = plan(summary)
    planner.first = intent(correct.model_copy(update={"table_id": "invalid"}))
    planner.revised = ProviderError("insufficient_quota") if quota else intent(correct)
    response = post(api, "Amount 합계")
    assert len(planner.questions) == len(planner.repairs) == 1
    assert "secret-token" not in response.text
    if quota:
        assert response.status_code == 502 and "detail" in response.json()
    else:
        assert response.status_code == 200
        body = response.json()
        assert "합계 100" in body["answer"] and body["verification"]["level"] == "request_checked"
        assert "plan_replanned" in body["verification"]["checks"]
