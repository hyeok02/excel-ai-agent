"""Resolved follow-ups re-read source cells without upgrading inferred scope."""
import asyncio

from app.agent import create_default_tool_registry
from app.agent.query.conversation_models import ContextResolutionDraft, QuestionConversation
from app.agent.query.service import WorkbookQuestionService
from tests.support.large_workbook_fixtures import ForbiddenExternalCall, NoGeneratedAnswer, offline
from tests.support.trend_adversarial_fixtures import QUESTION, source

RESOLVED = f"Arbitrary 시트에서 {QUESTION}"


class NoClassifier:
    async def classify(self, *args):
        raise ForbiddenExternalCall("A source-bound trend must not invoke model classification")


class Resolver:
    async def resolve(self, question, context):
        return ContextResolutionDraft(status="resolved", question=RESOLVED, context_ids=["turn:0"])


def _service():
    return WorkbookQuestionService(NoGeneratedAnswer(), create_default_tool_registry(),
                                   classifier=NoClassifier(), context_resolver=Resolver())


def test_trend_followup_retains_rebound_but_downgrades_inferred_request_scope():
    summary, index = source()
    context = QuestionConversation(turns=[{
        "question": "전체 직원 수는 얼마야?", "evidence": ["Arbitrary!A1:B5"],
    }])
    answer = asyncio.run(_service().answer("그럼 그 항목의 추이는?", summary, index, context))
    assert answer.status == "limited", answer.model_dump()
    assert answer.resolved_question == RESOLVED
    assert "반등" in answer.answer
    assert answer.verification.level == "source_checked"
    assert "context_resolved" in answer.verification.checks
    assert "request_alignment" not in answer.verification.checks


def test_trend_followup_cannot_reuse_another_files_evidence_addresses():
    summary, index = source()
    context = QuestionConversation(turns=[{
        "question": "전체 직원 수는 얼마야?", "evidence": ["OtherWorkbook!A1:B5"],
    }])
    answer = asyncio.run(_service().answer("그럼 그 항목의 추이는?", summary, index, context))
    assert answer.status == "insufficient_evidence", answer.model_dump()
    assert answer.verification.level == "unverified"
    assert answer.selected_tools == ["clarify_question_context"]


def test_trend_followup_never_reuses_prior_numeric_results_for_current_bytes():
    context = QuestionConversation(turns=[{
        "question": "전체 직원 수는 얼마야?", "evidence": ["Arbitrary!A1:B5"],
    }])
    for values, rebound in [([100, 150, 120, 130], True), ([700, 600, 500, 400], False)]:
        summary, index = source(values)
        answer = asyncio.run(_service().answer("그럼 그 항목의 추이는?", summary, index, context))
        assert answer.status == "limited", answer.model_dump()
        assert answer.verification.level == "source_checked"
        assert ("반등" in answer.answer) == rebound
        assert str(values[0]) in answer.answer and str(values[-1]) in answer.answer
