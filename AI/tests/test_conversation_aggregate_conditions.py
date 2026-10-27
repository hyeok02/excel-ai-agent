import asyncio

import pytest

from app.agent import create_default_tool_registry
from app.agent.query.conversation_models import QuestionConversation
from app.agent.query.service import WorkbookQuestionService
from tests.support.large_workbook_fixtures import NoGeneratedAnswer
from tests.tabular_query_fixtures import table_fixture


def _run(question, previous="Zone가 East인 Amount 합계", evidence=None, pending=False):
    summary,index=table_fixture([(1,1,[["Zone","Amount","Score"],["East",10,2],["East",20,4],["West",9,8]])])
    context=QuestionConversation(turns=[{"question":previous,"needs_clarification":pending,
        "evidence":evidence if evidence is not None else ["Arbitrary!A1:B4"]}])
    return asyncio.run(WorkbookQuestionService(NoGeneratedAnswer(),create_default_tool_registry()).answer(
        question,summary,index,context))


@pytest.mark.parametrize("prefix", ["그 조건에서", "같은 조건에서", "동일한 조건으로"])
def test_same_conditions_rebinds_requested_metric_and_keeps_filter(prefix):
    result=_run(prefix+" Score 합계는?")
    assert result.status == "limited" and "6" in result.answer
    assert result.verification.level == "source_checked"
    assert "East" in result.resolved_question and "Score" in result.resolved_question


@pytest.mark.parametrize("updates", [
    {"previous":"Zone가 East인 미승인 Amount 합계"},
    {"previous":"Zone가 East인 Amount 합계를 두 배로"},
    {"evidence":["DifferentFile!A1:B4"]}, {"pending":True},
])
def test_unproven_or_unresolved_parent_conditions_are_not_inherited(updates):
    result=_run("그 조건에서 Score 합계는?",**updates)
    assert result.status == "insufficient_evidence" and result.verification.level == "unverified"


def test_followup_extra_condition_is_not_silently_dropped():
    result=_run("그 조건에서 미승인 Score 합계는?")
    assert result.status == "insufficient_evidence"
