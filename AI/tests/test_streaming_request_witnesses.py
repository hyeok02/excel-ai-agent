"""Full-source guards and conversational anchors survive bounded indexing."""
import asyncio

import pytest

from app.agent import create_default_tool_registry
from app.agent.query.conversation_models import QuestionConversation
from app.agent.query.conversation_sources import source_bound_context
from app.agent.query.service import WorkbookQuestionService
from tests.support.large_workbook_fixtures import (
    FixedClassifier, NoGeneratedAnswer, ask, assert_not_certified, assert_stream_checked,
    fresh_index, offline, parsed, plan_for, tiny_caps, workbook,
)
from tests.test_large_workbook_boundaries import row_limit_source
from tests.test_source_context_readback import Resolver


@pytest.mark.parametrize("source_value,spelling", [("İstanbul", "istanbul"), ("ıstanbul", "Istanbul")])
def test_tail_case_insensitive_category_cannot_escape_request_witnesses(tiny_caps, source_value, spelling):
    rows = [["Record", "Amount", "Group"],
            *[[f"Item{number}", number, "ordinary"] for number in range(1, 9)],
            ["Tail", 888, source_value]]
    summary, index, _ = parsed(workbook({"Records": rows}))
    # re.IGNORECASE used by the request guards accepts these spellings. A
    # narrower casefold substring prefilter must not erase the tail predicate.
    response = ask(f"Records 시트 {spelling} 항목의 Amount 합계는?", summary, index, plan_for(summary))
    assert_not_certified(response)
    assert "합계 924" not in response.answer


def test_large_aggregate_keeps_source_anchor_for_verified_followup(row_limit_source):
    summary, _, content = row_limit_source
    question = "Records 시트 Amount 합계는?"
    first = ask(question, summary, fresh_index(summary, content), plan_for(summary))
    assert_stream_checked(first)
    assert "합계 20,000" in first.answer
    assert any(item.reference == "B1:B10003" for item in first.evidence)
    assert any(item.reference == "B1" and item.value == "Amount" for item in first.evidence)
    conversation = QuestionConversation(turns=[{
        "question": question,
        "evidence": [f"{item.sheet_name}!{item.reference}" for item in first.evidence],
    }])
    index = fresh_index(summary, content)
    context = source_bound_context(conversation, summary, index)
    assert len(context) == 1
    assert any(cell["reference"] == "Records!B1" and cell["value"] == "Amount"
               for cell in context[0]["source_cells"])
    resolver = Resolver("Records 시트 Amount 최댓값은?")
    service = WorkbookQuestionService(
        NoGeneratedAnswer(), create_default_tool_registry(),
        classifier=FixedClassifier(plan_for(summary, statistic="max")), context_resolver=resolver,
    )
    response = asyncio.run(service.answer("그럼 최댓값은?", summary, index, conversation))
    assert response.resolved_question == resolver.resolved
    assert "최댓값 9,999" in response.answer
    assert response.status == "limited" and response.verification.level == "source_checked"
    assert {"context_resolved", "full_source_scan"} <= set(response.verification.checks)
    assert resolver.seen[0]["source_cells"]
