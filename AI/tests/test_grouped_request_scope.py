"""Grouped answers must prove requested dimensions, measures and operation."""
import pytest

from app.agent.query.tabular_binding import bind_tabular_plan
from app.agent.query.tabular_catalog import build_query_tables
from app.agent.query.tabular_query_models import TabularQueryPlan, TabularFilter
from app.agent.query.tabular_request_scope import request_matches_plan
from tests.tabular_query_fixtures import table_fixture


def _table():
    summary, _ = table_fixture([(1, 1, [
        ["부서", "지역", "Amount", "Score"], ["Alpha", "East", 10, 3], ["Beta", "West", 20, 9],
    ])])
    return build_query_tables(summary)[0]


def _plan(table, **updates):
    return TabularQueryPlan(operation="numeric_summary", table_id=table.id, column_ids=["C"],
                            group_by=["A"], statistic="sum").model_copy(update=updates)


@pytest.mark.parametrize("question,groups", [
    ("부서별 Amount 합계", ["A"]), ("sum Amount by 부서", ["A"]),
    ("'부서'별 'Amount' 합계", ["A"]), ("sum 'Amount' by '부서'", ["A"]),
    ("부서와 지역별 Amount 합계", ["A", "B"]),
    ("부서별, 지역별 Amount 합계", ["A", "B"]),
    ("sum Amount grouped by 부서 and 지역", ["A", "B"]),
])
def test_source_dimensions_are_independently_bound(question, groups):
    table = _table()
    assert request_matches_plan(question, _plan(table, group_by=groups), table, [table], streaming=True)


@pytest.mark.parametrize("question,updates", [
    ("부서별 Amount 합계", {"group_by": []}),
    ("부서별 Amount 합계", {"group_by": ["B"]}),
    ("부서별 Amount 합계", {"group_by": ["A", "B"]}),
    ("부서와 지역별 Amount 합계", {"group_by": ["A"]}),
    ("Amount 합계", {}), ("unknown별 Amount 합계", {}),
    ("sum Amount by 부서 and Unknown", {}),
    ("부서별 Amount 합계", {"column_ids": ["A"]}),
    ("부서별 Amount 합계", {"column_ids": ["D"]}),
    ("부서별 Amount 합계와 평균", {"statistic": "all"}),
    ("부서별 Amount와 Score 요약", {"statistic": "all"}),
    ("부서별 Amount 요약", {"statistic": "all", "column_ids": ["C", "D"]}),
    ("부서별 Amount 중앙값", {"statistic": "all"}),
    ("부서별 요약", {"statistic": "all"}),
    ("부서별 Amount 합계", {"statistic": "all"}),
    ("부서별 Amount 합계가 100 이상인 그룹", {}),
    ("부서별 Amount 합계 비중", {}),
    ("부서별 Amount 합계를 Score로 나눈 비율", {}),
    ("부서별 Amount 합계 / 100", {}), ("부서별 Amount 합계의 10%", {}),
    ("부서별 Amount 합계 두 배", {}), ("부서별 Amount 합계에서 10을 빼줘", {}),
    ("부서별 중복 제거 건수", {"operation": "row_count", "column_ids": []}),
])
def test_wrong_or_unsupported_grouped_plan_never_verifies(question, updates):
    table = _table()
    assert not request_matches_plan(question, _plan(table, **updates), table, [table], streaming=True)


def test_group_dimensions_cannot_smuggle_the_selected_metric_into_a_filter():
    table = _table()
    plan = _plan(table, column_ids=["D"], filters=[TabularFilter(
        column_id="C", operator="greater_than", value=1)])
    assert not request_matches_plan("Amount가 1 초과인 행의 부서별 Amount 합계", plan, table, [table])


def test_grouped_count_cannot_answer_a_sum_and_all_summary_is_allowed():
    table = _table()
    count = _plan(table, operation="row_count", column_ids=[])
    assert request_matches_plan("부서별 건수", count, table, [table], streaming=True)
    assert not request_matches_plan("부서별 Amount 합계", count, table, [table], streaming=True)
    assert request_matches_plan("부서별 Amount 요약", _plan(table, statistic="all"), table, [table])


def test_group_labels_are_bound_like_selected_source_headers():
    table = _table()
    plan = _plan(table, column_ids=["Amount"], group_by=["부서"])
    bound = bind_tabular_plan(plan, table)
    assert bound.group_by == ["A"] and bound.column_ids == ["C"]
    assert bind_tabular_plan(_plan(table, group_by=["Not a source"]), table) is None


def test_legacy_frequency_request_does_not_require_a_group_plan():
    table = _table()
    plan = _plan(table, operation="frequencies", column_ids=["A"], group_by=[])
    assert request_matches_plan("부서별 건수", plan, table, [table])


def test_group_word_in_quoted_filter_value_does_not_authorize_grouping():
    from app.agent.query.tabular_request_grouping import grouping_constraints_match

    table = _table()
    assert not grouping_constraints_match("지역이 '부서별'인 Amount 합계", _plan(table), table)


@pytest.mark.parametrize("question", ["Amount가 -10 이상인 행의 부서별 Amount 합계",
                                     "Score가 10% 이상인 행의 부서별 Amount 합계"])
def test_source_threshold_sign_and_percentage_are_not_post_aggregate_math(question):
    from app.agent.query.tabular_request_grouping import grouping_constraints_match

    table = _table()
    assert grouping_constraints_match(question, _plan(table), table)


def test_source_header_division_symbol_is_not_post_aggregate_math():
    from app.agent.query.tabular_request_grouping import grouping_constraints_match
    from dataclasses import replace

    table = _table()
    table = replace(table, columns=tuple(replace(column, header="Cost/Unit") if column.id == "C" else column
                                         for column in table.columns))
    assert grouping_constraints_match("부서별 Cost/Unit 합계", _plan(table), table)
