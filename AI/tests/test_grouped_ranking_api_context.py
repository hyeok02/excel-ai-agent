"""API source isolation and follow-up scope stay independent of live AI calls."""
import asyncio

from fastapi.testclient import TestClient
import pytest

from app.agent import create_default_tool_registry
from app.agent.query.conversation_models import ContextResolutionDraft, QuestionConversation
from app.agent.query.service import WorkbookQuestionService
from app.api import workbook_questions as endpoint
from app.main import app
from tests.support.grouped_ranking_fixtures import grouped_plan, line_with, records, source
from tests.support.large_workbook_fixtures import (
    FixedClassifier, NoGeneratedAnswer, ask, assert_stream_checked, fresh_index, offline, tiny_caps,
)


@pytest.fixture
def client():
    saved = dict(app.dependency_overrides)
    app.dependency_overrides[endpoint.get_question_answer_generator] = lambda: NoGeneratedAnswer()
    app.dependency_overrides[endpoint.get_question_context_resolver] = lambda: None
    with TestClient(app) as result:
        yield result
    app.dependency_overrides.clear()
    app.dependency_overrides.update(saved)


def test_api_group_ranking_uses_fresh_uploaded_original_each_time(client, tiny_caps, monkeypatch):
    summary, _, original = source()
    changed = records()
    changed[-1][1] = 10_000
    _, _, other = source(changed)
    plan = grouped_plan(summary, order_by="B", limit=1)
    monkeypatch.setattr(endpoint, "_intent_classifier", FixedClassifier(plan))
    for content, expected in [(original, "합계 970"), (other, "합계 10,900"), (original, "합계 970")]:
        response = client.post("/api/v1/workbooks/questions",
                               data={"question": "Records 시트 Department별 Amount 합계 상위 1개 보여줘"},
                               files={"file": ("same-name.xlsx", content)})
        assert response.status_code == 200, response.text
        body = response.json()
        assert body["status"] == "answered", body
        assert expected in body["answer"]
        assert body["verification"]["level"] == "request_checked"
        assert "full_source_scan" in body["verification"]["checks"]


class Resolver:
    def __init__(self, resolved):
        self.resolved, self.seen = resolved, None

    async def resolve(self, question, context):
        self.seen = context
        return ContextResolutionDraft(status="resolved", question=self.resolved, context_ids=["turn:0"])


def test_followup_changes_group_statistic_using_original_not_prior_ranked_subset(tiny_caps):
    summary, index, content = source()
    first_question = "Records 시트 Department별 Amount 합계 상위 2개 보여줘"
    first = ask(first_question, summary, index, grouped_plan(summary, order_by="B", limit=2))
    assert_stream_checked(first)
    resolved = "Records 시트 Department별 Amount 평균 상위 2개 보여줘"
    resolver = Resolver(resolved)
    service = WorkbookQuestionService(NoGeneratedAnswer(), create_default_tool_registry(),
                                     classifier=FixedClassifier(grouped_plan(
                                         summary, statistic="average", order_by="B", limit=2)),
                                     context_resolver=resolver)
    context = QuestionConversation(turns=[{
        "question": first_question,
        "evidence": [f"{item.sheet_name}!{item.reference}" for item in first.evidence],
    }])
    answer = asyncio.run(service.answer("그럼 평균 기준 상위 2개는?", summary,
                                       fresh_index(summary, content), context))
    assert answer.resolved_question == resolved, answer.model_dump()
    assert "평균 485" in line_with(answer, "Delta")
    assert "평균 8" in line_with(answer, "Beta")
    assert answer.status == "limited"
    assert answer.verification.level == "source_checked"
    assert {"context_resolved", "full_source_scan"} <= set(answer.verification.checks)
    assert resolver.seen
