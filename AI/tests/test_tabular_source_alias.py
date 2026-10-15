"""Unknown target translations must remain explicit and below green verification."""
from dataclasses import replace
import pytest

from app.agent.query.ambiguity_answers import ambiguous_source_answer
from app.agent.query.intent_models import QuestionIntent
from app.agent.query.models import QuestionAnswer, QuestionAnswerStatus
from app.agent.query.tabular_catalog import build_query_tables
from app.agent.query.tabular_query_models import TabularFilter, TabularQueryPlan
from app.agent.query.tabular_source_alias import source_label_alias_answer
from tests.tabular_query_fixtures import table_fixture


def _fixture(question="라일락 직원 수는 몇 명이야?", rows=None):
    rows = rows or [["Lilac", 107], ["Rose", 99]]
    summary, index = table_fixture([
        (2, 1, [["Entity", "Total Employees"], *rows]),
        (9, 1, [["Office", "Total Employees"], ["North", 3], ["East", 7]]),
    ])
    plan = TabularQueryPlan(operation="lookup", table_id=build_query_tables(summary)[0].id,
                            column_ids=["B"], filters=[
                                TabularFilter(column_id="A", operator="equals", value="Lilac"),
                            ])
    intent = QuestionIntent(False, "cell_lookup", (), True, plan)
    clarification = ambiguous_source_answer(question, summary, index, intent)
    return question, summary, index, intent, clarification


@pytest.mark.parametrize("question", ["라일락 직원 수는 몇 명이야?", "라일락의 직원 수는 몇 명이야?"])
def test_literal_source_alias_is_exposed_but_never_request_checked(question):
    args = _fixture(question)
    assert args[-1] is not None
    answer = source_label_alias_answer(*args)
    assert answer is not None and answer.status == "limited"
    assert answer.verification.level == "source_checked"
    assert "request_alignment" not in answer.verification.checks
    assert "semantic_alias_resolved" in answer.verification.checks
    assert "라일락(Lilac)" in answer.resolved_question
    assert "‘라일락’" in answer.answer and "‘Lilac’" in answer.answer and "107" in answer.answer


@pytest.mark.parametrize("question", [
    "라일락 Rose 직원 수는 몇 명이야?", "라일락의 정규직 직원 수는 몇 명이야?",
    "라일락의 2024년 직원 수는 몇 명이야?", "라일락이 아닌 직원 수는 몇 명이야?",
    "라일락과 장미 직원 수는 몇 명이야?", "전체 직원 수는 몇 명이야?",
    "라일락의 직원 수를 천 명 단위로 보여줘", "라일락의 직원 수 평균은 얼마야?",
])
def test_alias_cannot_silently_drop_qualifiers_or_other_targets(question):
    args = list(_fixture(question))
    args[-1] = args[-1] or _clarification(question)
    assert source_label_alias_answer(*args) is None


@pytest.mark.parametrize("rows", [
    [["Lilac", 107], ["Lilac", 999]], [["Lilac", 107], ["라일락", 999]],
    [["Rose", 107], ["Lily", 999]],
])
def test_alias_needs_one_existing_row_and_no_conflicting_original_label(rows):
    args = list(_fixture(rows=rows))
    args[-1] = args[-1] or _clarification(args[0])
    assert source_label_alias_answer(*args) is None


@pytest.mark.parametrize("change", [
    {"from_model": False}, {"kind": "row_list"}, {"whole_workbook": True},
])
def test_alias_requires_model_scalar_intent(change):
    args = list(_fixture())
    args[3] = replace(args[3], **change)
    assert source_label_alias_answer(*args) is None


def _clarification(question):
    return QuestionAnswer(question=question, answer="choose a source", status=QuestionAnswerStatus.INSUFFICIENT_EVIDENCE,
                          confidence=0, selected_tools=["clarify_source_scope"], evidence=[], limitations=[])
