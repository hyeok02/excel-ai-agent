"""The executor uses the guard's own resolver: a classifier-chosen table is not
request-checked while another table answers the same plan with other values."""
import asyncio

from app.agent.query.intent_models import QuestionIntent
from app.agent.query.tabular_catalog import build_query_tables
from app.agent.query.tabular_execution import execute_tabular_query
from app.agent.query.tabular_query_models import TabularFilter, TabularQueryPlan
from app.agent.query.tabular_routing import planned_tabular_answer
from tests.tabular_query_fixtures import table_fixture
from tests.test_ambiguity_service import _service

OWNERS = [["Owner", "Amount"], ["Alpha", 10], ["Beta", 20]]


def _two(second=None):
    return table_fixture([(2, 2, OWNERS), (2, 6, second or [["Owner", "Amount"], ["Alpha", 70], ["Beta", 80]])])


def _sum(table, column="C"):
    return TabularQueryPlan(operation="numeric_summary", table_id=table.id, column_ids=[column], statistic="sum")


def _ask(question, plan, summary, index, kind="aggregation"):
    intent = QuestionIntent(False, kind, (), True, plan)
    return asyncio.run(_service(intent).answer(question, summary, index))


def test_unnamed_field_or_no_field_cannot_pick_one_of_two_valued_tables():
    summary, index = _two()
    for table in build_query_tables(summary):
        column = "C" if table.reference.startswith("B") else "G"
        for question in ["합계는?", "총합 알려줘", "Amount 합계는?", "Amount 변동 합계는?",
                         "두 표를 연결해서 Amount 합계 알려줘"]:
            assert execute_tabular_query(_sum(table, column), summary, index, question) is None
        answer = _ask("합계는?", _sum(table, column), summary, index)
        assert answer.status == "insufficient_evidence" and answer.verification.level == "unverified"
        assert answer.selected_tools == ["clarify_source_scope"]
        assert len(answer.clarification_options) == 2
        assert "B2:C4" in answer.answer and "F2:G4" in answer.answer
        assert "30" not in answer.answer and "150" not in answer.answer


def test_row_count_without_fields_compares_whole_table_shape():
    summary, index = _two([["Owner", "Amount"], ["Alpha", 70], ["Beta", 80], ["Gamma", 90]])
    plan = TabularQueryPlan(operation="row_count", table_id=build_query_tables(summary)[0].id)
    assert execute_tabular_query(plan, summary, index, "몇 건이야?") is None
    summary, index = _two([["Owner", "Amount"], ["Alpha", 70], ["Beta", 80], ["Gamma", 90]])
    plan = TabularQueryPlan(operation="row_count", table_id=build_query_tables(summary)[0].id)
    answer = planned_tabular_answer(QuestionIntent(False, "row_count", (), True, plan), summary, index, "몇 건이야?")
    assert answer.selected_tools == ["clarify_source_scope"]  # 2 rows vs 3 rows
    summary, index = _two()  # different values, same number of rows: one count
    plan = TabularQueryPlan(operation="row_count", table_id=build_query_tables(summary)[0].id)
    assert "2건" in execute_tabular_query(plan, summary, index, "몇 건이야?").answer


def test_named_scope_or_identity_value_still_answers_from_the_selected_table():
    summary, index = _two()
    first, second = build_query_tables(summary)
    assert "합계 30" in _ask("Arbitrary!B2:C4 범위 Amount 합계는?", _sum(first), summary, index).answer
    answer = _ask("Arbitrary!F2:G4 범위의 G열 Amount 기준으로: 합계는?", _sum(second, "G"), summary, index)
    assert "합계 150" in answer.answer and answer.verification.level == "request_checked"
    summary, index = _two([["Owner", "Amount"], ["Gamma", 70], ["Delta", 80]])
    second = build_query_tables(summary)[1]
    plan = TabularQueryPlan(operation="lookup", table_id=second.id, column_ids=["G"],
                            filters=[TabularFilter(column_id="F", operator="equals", value="Gamma")])
    answer = execute_tabular_query(plan, summary, index, "Gamma Amount 알려줘")
    assert "70" in answer.answer and answer.verification.level == "request_checked"
    wrong = plan.model_copy(update={"table_id": build_query_tables(summary)[0].id, "column_ids": ["C"],
                                    "filters": [TabularFilter(column_id="B", operator="equals", value="Gamma")]})
    assert execute_tabular_query(wrong, summary, index, "Gamma Amount 알려줘") is None


def test_identical_copy_or_table_missing_a_planned_field_is_not_a_rival():
    summary, index = _two(OWNERS)
    table = build_query_tables(summary)[0]
    assert "합계 30" in execute_tabular_query(_sum(table), summary, index, "합계는?").answer
    summary, index = _two([["Owner", "Score"], ["Alpha", 70], ["Beta", 80]])
    table = build_query_tables(summary)[0]
    assert "합계 30" in execute_tabular_query(_sum(table), summary, index, "합계는?").answer


def test_single_table_is_never_blocked_by_the_rival_check():
    summary, index = table_fixture([(2, 2, OWNERS)])
    table = build_query_tables(summary)[0]
    assert "합계 30" in execute_tabular_query(_sum(table), summary, index, "합계는?").answer
    count = TabularQueryPlan(operation="row_count", table_id=table.id)
    assert "2건" in execute_tabular_query(count, summary, index, "몇 건이야?").answer
