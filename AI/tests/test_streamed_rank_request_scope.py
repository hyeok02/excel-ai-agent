"""A bounded witness sample cannot establish source-rank population semantics."""
import pytest

from app.agent.query.tabular_catalog import build_query_tables
from app.agent.query.tabular_query_models import TabularQueryPlan, TabularFilter
from app.agent.query.tabular_request_scope import request_matches_plan
from tests.tabular_query_fixtures import table_fixture


def _fixture():
    summary, _ = table_fixture([(1, 1, [
        ["부서", "Amount", "Score", "Rank"], ["Alpha", 10, 3, 2], ["Beta", 20, 9, 1],
    ])])
    table = build_query_tables(summary)[0]
    plan = TabularQueryPlan(operation="row_list", table_id=table.id, column_ids=["B", "C"],
                            order_by="B", descending=True, limit=2)
    return table, plan


@pytest.mark.parametrize("question,descending", [
    ("Amount 상위 2개", True), ("Amount 하위 2개", False),
    ("Amount가 낮은 2개", False), ("Amount 높은 2개", True),
    ("Amount 오름차순 2개", False), ("Amount 내림차순 2개", True),
    ("top 2 rows by Amount", True), ("Amount ascending 2 rows", False),
])
def test_explicit_numeric_rank_order_and_count_remain_supported(question, descending):
    table, plan = _fixture()
    assert request_matches_plan(question, plan.model_copy(update={"descending": descending}),
                                table, [table], streaming=True)


@pytest.mark.parametrize("question,updates", [
    ("Amount 상위 2개", {"limit": 1}), ("Amount 상위 2개", {"descending": False}),
    ("Amount 상위 2개", {"order_by": "C"}), ("상위 2개", {}),
    ("Amount 상위 2개 동점 포함", {}), ("Amount top 2 including ties", {}),
    ("Amount 상위 2개 하위 2개", {}), ("Amount 상위 2개 오름차순", {}),
    ("Amount 상위 2개 중 Score 상위 1개", {}), ("Amount 보여줘", {}),
    ("Amount 상위 2개 합계", {}), ("Amount 상위 2개 평균", {}),
])
def test_unrequested_and_changed_rank_operations_are_rejected(question, updates):
    table, plan = _fixture()
    assert not request_matches_plan(question, plan.model_copy(update=updates), table, [table], streaming=True)


def test_streamed_source_rank_cannot_be_certified_from_permutation_witnesses():
    table, plan = _fixture()
    plan = plan.model_copy(update={"order_by": "D", "descending": False})
    assert request_matches_plan("Amount 상위 2개", plan, table, [table])
    assert not request_matches_plan("Amount 상위 2개", plan, table, [table], streaming=True)


@pytest.mark.parametrize("question,updates", [
    ("부서별 Amount 합계 상위 2개", {}),
    ("sum Amount by 부서 top 2", {}),
    ("top 2 sum Amount by 부서", {}),
    ("부서별 Amount 평균 하위 2개", {"statistic": "average", "descending": False}),
])
def test_group_rank_is_explicitly_an_aggregate_rank(question, updates):
    table, plan = _fixture()
    plan = plan.model_copy(update={"operation": "numeric_summary", "column_ids": ["B"],
                                   "group_by": ["A"], "statistic": "sum", **updates})
    assert request_matches_plan(question, plan, table, [table], streaming=True)


def test_group_count_ranking_requires_count_language_and_no_source_order():
    table, plan = _fixture()
    plan = plan.model_copy(update={"operation": "row_count", "column_ids": [],
                                   "group_by": ["A"], "order_by": None})
    assert request_matches_plan("부서별 건수 상위 2개", plan, table, [table], streaming=True)
    assert not request_matches_plan("부서별 상위 2개", plan, table, [table], streaming=True)
    assert not request_matches_plan("부서별 Amount 합계 상위 2개", plan, table, [table], streaming=True)
    assert not request_matches_plan("부서별 Amount 상위 2개 행개수", plan, table, [table], streaming=True)


@pytest.mark.parametrize("streaming", [False, True])
def test_sort_field_need_not_be_a_display_column(streaming):
    table, plan = _fixture()
    plan = plan.model_copy(update={"column_ids": ["A"]})
    assert request_matches_plan("Amount 상위 2개 부서만", plan, table, [table], streaming=streaming)
