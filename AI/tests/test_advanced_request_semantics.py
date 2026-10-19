"""Offline request verification does not trust advanced model-selected fields."""
import pytest

from app.agent.query.tabular_binding import bind_tabular_plan
from app.agent.query.tabular_catalog import build_query_tables
from app.agent.query.tabular_query_models import TabularQueryPlan, TabularAggregateCondition, TabularFilter
from app.agent.query.tabular_request_scope import request_matches_plan
from tests.tabular_query_fixtures import table_fixture


def fixture(**updates):
    summary, _ = table_fixture([(1, 1, [
        ["부서", "매출", "고객", "상태", "직원"],
        ["Alpha", 100, "One", "active", "A"], ["Beta", 200, "Two", "inactive", "B"],
    ])])
    table = build_query_tables(summary)[0]
    plan = TabularQueryPlan(operation="numeric_summary", table_id=table.id,
                            group_by=["A"], column_ids=["B"], statistic="sum").model_copy(update=updates)
    return table, plan


def checked(question, **updates):
    table, plan = fixture(**updates)
    return request_matches_plan(question, plan, table, [table], streaming=True)


def having(value=100000000, **updates):
    return TabularAggregateCondition(column_id="B", operator="greater_than", value=value).model_copy(update=updates)


@pytest.mark.parametrize("question,value", [
    ("부서별 매출 합계가 1억 넘는 부서만 보여줘", 100000000),
    ("부서별 매출 합계가 1억 2천만 넘는 부서만", 120000000),
    ("부서별 매출 합계가 1.5억 초과인 부서만", 150000000),
    ("부서별 매출 합계가 -1억 2천만 초과인 부서만", -120000000),
    ("sum 매출 by 부서 having sum 매출 > 100", 100),
])
def test_having_uses_fully_aggregated_measure_and_numeric_units(question, value):
    assert checked(question, having=[having(value)])


@pytest.mark.parametrize("mutation", [
    {"having": []}, {"having": [having(operator="greater_than_or_equal")]},
    {"having": [having(10000)]}, {"having": [having(column_id="C")]},
    {"having": [having(column_id=None)]}, {"having": [having(value_unit="percent")]},
    {"filters": [TabularFilter(column_id="B", operator="greater_than", value=100000000)]},
])
def test_missing_or_wrong_having_cannot_get_verification(mutation):
    assert not checked("부서별 매출 합계가 1억 넘는 부서만", **mutation)


def test_having_never_hides_an_ordinary_row_filter_with_the_same_threshold():
    question = "매출이 100 이상인 행의 부서별 매출 합계가 100 이상인 부서"
    condition = having(100, operator="greater_than_or_equal")
    assert not checked(question, having=[condition])
    assert checked(question, having=[condition], filters=[TabularFilter(
        column_id="B", operator="greater_than_or_equal", value=100)])


def test_a_count_having_cannot_be_rebound_to_the_numeric_sum():
    assert not checked("부서별 매출 합계와 건수가 2 미만인 부서", having=[having(2, operator="less_than")])


@pytest.mark.parametrize("question", ["부서별 전체 매출 비중은?", "부서별 매출 합계 비중", "share of total 매출 by 부서"])
def test_shares_require_the_source_measure_and_sum_population(question):
    assert checked(question, share_of_total=True)
    assert not checked(question)
    assert not checked(question, share_of_total=True, statistic="average")
    assert not checked(question, share_of_total=True, column_ids=["C"])


def test_share_having_uses_percentage_not_raw_amount():
    condition = having(25, column_id=None, target="share", value_unit="percent")
    question = "부서별 전체 매출 비중이 25% 이상인 부서만"
    assert checked(question, share_of_total=True, having=[condition.model_copy(update={"operator": "greater_than_or_equal"})])
    assert not checked(question, share_of_total=True, having=[having(25)])


@pytest.mark.parametrize("question", ["상태가 active인 부서별 전체 원본 매출 비중",
                                     "상태가 active인 부서별 매출 비중을 필터와 관계없이 계산"])
def test_share_may_not_reuse_filtered_denominator_when_unfiltered_population_is_requested(question):
    assert not checked(question, share_of_total=True, filters=[TabularFilter(
        column_id="D", operator="equals", value="active")])


@pytest.mark.parametrize("question", ["중복 제외한 고객 수", "고객 중복 제거 건수", "count distinct 고객", "number of unique 고객"])
def test_distinct_count_requires_the_named_source_key(question):
    assert checked(question, operation="distinct_count", group_by=[], column_ids=["C"])
    assert not checked(question, operation="row_count", group_by=[], column_ids=[])
    assert not checked(question, operation="distinct_count", group_by=[], column_ids=["E"])


def test_grouped_distinct_and_exact_label_binding():
    assert checked("부서별 중복 제외한 고객 수", operation="distinct_count", column_ids=["C"])
    table, plan = fixture(having=[having(column_id="매출")], column_ids=["매출"], group_by=["부서"])
    bound = bind_tabular_plan(plan, table)
    assert bound.having[0].column_id == "B" and bound.column_ids == ["B"] and bound.group_by == ["A"]


def test_distinct_tuple_and_row_count_share_are_separate_common_operations():
    assert checked("부서와 고객 조합의 중복 제외 개수", operation="distinct_count", group_by=[], column_ids=["A", "C"])
    assert not checked("부서와 고객 조합의 중복 제외 개수", operation="distinct_count", group_by=[], column_ids=["C"])
    assert checked("부서별 행 개수의 전체 비중", operation="row_count", column_ids=[], share_of_total=True)
    assert not checked("부서별 행 개수의 전체 비중", operation="row_count", column_ids=[], share_of_total=False)


def test_count_having_allows_numeric_magnitude_without_inventing_currency():
    options = dict(operation="row_count", column_ids=[], having=[having(
        10000, column_id=None, operator="greater_than_or_equal")])
    assert checked("부서별 건수가 1만 이상인 부서", **options)
    assert not checked("부서별 건수가 1만원 이상인 부서", **options)


@pytest.mark.parametrize("question", ["각 부서에서 매출 상위 3명씩", "부서별 매출 상위 3명씩", "부서마다 매출 상위 3명씩"])
def test_per_group_ranking_is_not_global_ranking_or_an_aggregate(question):
    options = dict(operation="row_list", column_ids=["E", "B"], identity_column_ids=["E"], order_by="B", per_group_limit=3)
    assert checked(question, **options)
    for changes in ({"per_group_limit": None, "limit": 3}, {"descending": False},
                    {"per_group_limit": 2}, {"group_by": []}, {"identity_column_ids": []}):
        assert not checked(question, **(options | changes))


def test_explicit_raw_rows_need_no_invented_entity_identity():
    options = dict(operation="row_list", column_ids=["E", "B"], order_by="B", per_group_limit=3)
    assert checked("각 부서에서 매출 상위 3행씩", **options)
    assert checked("top 3 rows by 매출 per 부서", **options)


@pytest.mark.parametrize("question", ["부서별 매출 중앙값", "부서별 매출 합계를 2로 나눈 비율",
                                     "부서별 매출 합계 두 배", "부서별 전체 시트 매출 비중"])
def test_unsupported_derived_operations_still_fail_closed(question):
    assert not checked(question, share_of_total="비중" in question)
