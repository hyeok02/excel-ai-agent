"""Offline API contracts for context validation and conservative resolution failures."""
import json

import pytest
from fastapi.testclient import TestClient

from app.agent.query.conversation_models import ContextResolutionDraft
from app.agent.query.models import QuestionAnswer, QuestionAnswerVerification
from app.agent.query.service import WorkbookQuestionService
from app.api.workbook_questions import get_question_answer_generator, get_question_context_resolver
from app.main import app
from tests.test_conversation_sources import conversation_fixture


class StubResolver:
    def __init__(self, status="resolved", question="Notebook의 February 값은?", fail=False):
        self.status, self.question, self.fail, self.calls = status, question, fail, []

    async def resolve(self, question, entries):
        self.calls.append((question, entries))
        if self.fail:
            raise RuntimeError("resolver unavailable")
        return ContextResolutionDraft(status=self.status, question=self.question, context_ids=["turn:0"])


@pytest.fixture
def api(monkeypatch):
    calls = []

    async def current(_service, question, sources):
        calls.append((question, sources))
        return QuestionAnswer(question=question, answer="20", status="answered", confidence=1,
                              selected_tools=[], evidence=[], limitations=[], verification=QuestionAnswerVerification(
                                  level="request_checked", checks=["table_scope", "source_values", "request_alignment"]))

    monkeypatch.setattr(WorkbookQuestionService, "_answer_prepared", current)
    app.dependency_overrides[get_question_answer_generator] = lambda: object()
    app.dependency_overrides[get_question_context_resolver] = lambda: None
    try:
        yield TestClient(app), calls
    finally:
        app.dependency_overrides.pop(get_question_answer_generator, None)
        app.dependency_overrides.pop(get_question_context_resolver, None)


def _ask(api, context=None, question="그럼 February 값은?", include_hidden=False):
    content, _, _ = conversation_fixture()
    data = {"question": question, "include_hidden_sheets": str(include_hidden).lower()}
    if context is not None:
        data["context"] = context if isinstance(context, str) else json.dumps(context)
    return api[0].post("/api/v1/workbooks/questions", data=data, files={"file": ("current.xlsx", content)})


def _context(reference="Sales!A1:C3"):
    return {"turns": [{"question": "Notebook의 January 값은?", "evidence": [reference]}]}


@pytest.mark.parametrize("context", [
    "not json", "null", "[]", {"answer": "copied answer"},
    {"turns": [None]}, {"insights": [None]}, {"turns": _context()["turns"] * 7},
    {"insights": [{"title": "topic", "evidence": []}] * 7},
    {"turns": [{"question": "x" * 1001}]},
    {"turns": [{"question": "before", "answer": "copied prose"}]},
    {"insights": [{"title": "topic", "fact": "copied fact"}]},
    {"insights": [{"title": "x" * 201}]},
    {"insights": [{"title": "topic", "topic": "x" * 201}]},
    {"turns": [{"question": "before", "evidence": ["Sales!A1"] * 13}]},
    {"turns": [{"question": "before", "evidence": [None]}]},
    {"turns": [{"question": "before", "evidence": ["x" * 201]}]},
    " " * 24_001,
])
def test_api_rejects_malformed_oversized_or_fact_carrying_context(api, context):
    assert _ask(api, context).status_code == 422
    assert api[1] == []


@pytest.mark.parametrize("question", ["Sales!B2 값은?", "Are Notebook and Monitor the same item?"])
def test_api_legacy_standalone_request_does_not_need_context_or_resolver(api, question):
    response = _ask(api, question=question)
    assert response.status_code == 200
    assert response.json()["resolved_question"] is None
    assert api[1][0][0] == question


@pytest.mark.parametrize("mode", ["unavailable", "failure", "ambiguous", "bad_reference", "hidden"])
def test_dependent_question_clarifies_without_untrusted_fallback(api, mode):
    resolver = None if mode == "unavailable" else StubResolver(
        status="ambiguous" if mode == "ambiguous" else "resolved", fail=mode == "failure")
    app.dependency_overrides[get_question_context_resolver] = lambda: resolver
    reference = {"bad_reference": "Other!A1", "hidden": "Hidden!A1:B1"}.get(mode, "Sales!A1:C3")
    response = _ask(api, _context(reference))
    assert response.status_code == 200
    assert response.json()["status"] == "insufficient_evidence"
    assert response.json()["verification"]["level"] == "unverified"
    assert api[1] == []
    if mode in {"bad_reference", "hidden"}:
        assert resolver.calls == []


def test_api_resolved_question_preserves_original_and_downgrades_inferred_scope(api):
    resolver = StubResolver()
    app.dependency_overrides[get_question_context_resolver] = lambda: resolver
    response = _ask(api, _context())
    body = response.json()
    assert response.status_code == 200
    assert body["question"] == "그럼 February 값은?"
    assert body["resolved_question"] == "Notebook의 February 값은?"
    assert body["status"] == "limited"
    assert body["verification"]["level"] == "source_checked"
    assert "context_resolved" in body["verification"]["checks"]
    assert "request_alignment" not in body["verification"]["checks"]
    assert api[1][0][0] == body["resolved_question"]
    assert "SECRET SOURCE" not in str(resolver.calls)


def test_standalone_question_survives_resolver_failure(api):
    app.dependency_overrides[get_question_context_resolver] = lambda: StubResolver(fail=True)
    response = _ask(api, _context(), question="Sales!B2 값은?")
    assert response.status_code == 200
    assert response.json()["question"] == "Sales!B2 값은?"
    assert len(api[1]) == 1


def test_api_only_exposes_hidden_context_when_hidden_sheets_are_requested(api):
    resolver = StubResolver(question="Private metric은 뭐야?")
    app.dependency_overrides[get_question_context_resolver] = lambda: resolver
    response = _ask(api, _context("Hidden!A1:B1"), question="그건 뭐야?", include_hidden=True)
    assert response.status_code == 200
    assert len(api[1]) == 1
    assert "SECRET SOURCE" in str(resolver.calls)
