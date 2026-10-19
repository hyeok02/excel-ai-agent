"""A source-correct calculation cannot certify an altered advanced request."""
import pytest

from tests.support.advanced_qna_fixtures import (
    condition, distinct_plan, group_plan, partition_plan, source,
)
from tests.support.large_workbook_fixtures import ask, assert_not_certified, equal, offline, tiny_caps


@pytest.mark.parametrize("changes", [
    {"having": []}, {"having": [condition(71)]},
    {"having": [condition(70, operator="greater_than_or_equal")]},
    {"having": [condition(70, column="D")]}, {"statistic": "average"},
    {"having": [], "filters": [{"column_id": "B", "operator": "greater_than", "value": 70}]},
])
def test_having_cannot_be_omitted_changed_or_replaced_with_row_filter(tiny_caps, changes):
    summary, index, _ = source()
    options = dict(having=[condition(70)])
    options.update(changes)
    answer = ask("Records 시트 Department별 Amount 합계가 70 초과인 그룹 보여줘", summary, index,
                 group_plan(summary, **options))
    assert_not_certified(answer)


@pytest.mark.parametrize("changes", [
    {"share_of_total": False}, {"statistic": "average"},
    {"filters": [equal("E", "active")]}, {"group_by": []},
])
def test_share_request_cannot_be_replaced_with_total_or_different_denominator(tiny_caps, changes):
    summary, index, _ = source()
    options = dict(share_of_total=True)
    options.update(changes)
    answer = ask("Records 시트 Department별 Amount 합계의 전체 비중 알려줘", summary, index,
                 group_plan(summary, **options))
    assert_not_certified(answer)


@pytest.mark.parametrize("changes", [
    {"operation": "row_count", "columns": ()}, {"operation": "frequencies"},
    {"columns": ("A",)}, {"columns": ("C", "D")}, {"group_by": ["C"]},
])
def test_distinct_request_is_not_row_count_frequency_or_different_key(tiny_caps, changes):
    summary, index, _ = source()
    answer = ask("Records 시트 Customer 중복 제외 개수 알려줘", summary, index,
                 distinct_plan(summary, **changes))
    assert_not_certified(answer)


@pytest.mark.parametrize("changes", [
    {"per_group_limit": None, "limit": 2, "group_by": []},
    {"per_group_limit": None, "limit": 2}, {"per_group_limit": 3},
    {"descending": False}, {"order_by": "D"}, {"group_by": ["E"]},
    {"filters": [equal("E", "active")]},
])
def test_partition_request_cannot_be_replaced_with_global_or_wrong_rank(tiny_caps, changes):
    summary, index, _ = source()
    answer = ask("Records 시트 각 Department별 Amount 상위 2개 Record와 Amount 보여줘", summary, index,
                 partition_plan(summary, **changes))
    assert_not_certified(answer)


@pytest.mark.parametrize("feature", ["having", "share", "distinct", "partition"])
def test_unrequested_advanced_feature_cannot_gain_request_checked_badge(tiny_caps, feature):
    summary, index, _ = source()
    if feature == "distinct":
        question, plan = "Records 시트 행 개수 알려줘", distinct_plan(summary)
    elif feature == "partition":
        question = "Records 시트 Amount 상위 2개 Record와 Amount 보여줘"
        plan = partition_plan(summary)
    else:
        question = "Records 시트 Department별 Amount 합계 알려줘"
        plan = group_plan(summary, **({"having": [condition(70)]} if feature == "having"
                                     else {"share_of_total": True}))
    assert_not_certified(ask(question, summary, index, plan))
