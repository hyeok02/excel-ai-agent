"""Discourse prefixes do not make a complete original-cell lookup dependent."""
import asyncio

import pytest

from app.agent import create_default_tool_registry
from app.agent.query.conversation_models import QuestionConversation
from app.agent.query.service import WorkbookQuestionService
from tests.support.large_workbook_fixtures import NoGeneratedAnswer, parsed, workbook


class NoModel:
    async def classify(self, *args):
        raise BaseException("Complete cell lookups must not classify")

    async def resolve(self, *args):
        raise BaseException("Complete cell lookups must not resolve context")


@pytest.mark.parametrize("prefix", ["그럼 ", "그러면 ", "Then ", "And "])
@pytest.mark.parametrize("context", [
    None, QuestionConversation(), QuestionConversation(turns=[{
        "question": "다른 파일의 값은?", "evidence": ["Other!A1"], "needs_clarification": True,
    }]),
])
def test_prefixed_explicit_lookup_uses_current_file_without_context_or_model(prefix, context):
    summary, index, _ = parsed(workbook({"Records": [["Item", "Amount"], ["Unit-A", 17]]}))
    service = WorkbookQuestionService(NoGeneratedAnswer(), create_default_tool_registry(),
                                     classifier=NoModel(), context_resolver=NoModel())
    question = prefix + "Records!B2 값은?"
    answer = asyncio.run(service.answer(question, summary, index, context))
    assert answer.question == question
    assert answer.answer == "Records!B2: 17"
    assert answer.status == "answered"
    assert answer.selected_tools == ["read_original_cells"]
    assert answer.verification.level == "request_checked"


def test_prefixed_reference_does_not_erase_unresolved_subset_condition():
    summary, index, _ = parsed(workbook({"Records": [["Item", "Amount"], ["Unit-A", 17]]}))
    service = WorkbookQuestionService(NoGeneratedAnswer(), create_default_tool_registry())
    answer = asyncio.run(service.answer("그럼 그중 Records!B2 값은?", summary, index,
                                       QuestionConversation()))
    assert answer.status == "insufficient_evidence"
    assert answer.verification.level == "unverified"
