"""The model may select IDs, but may not omit or change requested semantics."""
import pytest

from tests.support.grouped_ranking_fixtures import grouped_plan, raw_plan, source
from tests.support.large_workbook_fixtures import (
    ask, assert_not_certified, equal, offline, tiny_caps,
)


@pytest.mark.parametrize("mutation", ["group", "direction", "limit", "measure", "statistic", "filter"])
def test_wrong_grouped_plan_never_gets_request_verification(tiny_caps, mutation):
    summary, index, _ = source()
    plan = grouped_plan(summary, order_by="B", limit=2)
    changes = {
        "group": {"group_by": []}, "direction": {"descending": False},
        "limit": {"limit": 3}, "measure": {"order_by": "A"},
        "statistic": {"statistic": "average"}, "filter": {"filters": [equal("D", "active")]},
    }
    plan = plan.model_copy(update=changes[mutation])
    answer = ask("Records 시트 Department별 Amount 합계 상위 2개 보여줘", summary, index, plan)
    assert_not_certified(answer)


@pytest.mark.parametrize("changes", [
    {"order_by": "A"}, {"order_by": None}, {"limit": None}, {"limit": 3},
    {"descending": False}, {"filters": [equal("D", "active")]},
])
def test_wrong_raw_ranking_plan_never_gets_request_verification(tiny_caps, changes):
    summary, index, _ = source()
    plan = raw_plan(summary).model_copy(update=changes)
    answer = ask("Records 시트 Amount 상위 2개 Record와 Amount 보여줘", summary, index, plan)
    assert_not_certified(answer)


@pytest.mark.parametrize("grouped", [False, True])
def test_tail_only_filter_cannot_be_omitted_while_ranking(tiny_caps, grouped):
    summary, index, _ = source()
    plan = grouped_plan(summary, order_by="B", limit=2) if grouped else raw_plan(summary)
    question = ("Records 시트 Department가 Delta인 Department별 Amount 합계 상위 2개 보여줘"
                if grouped else "Records 시트 Department가 Delta인 Amount 상위 2개 Record와 Amount 보여줘")
    assert_not_certified(ask(question, summary, index, plan))


def test_unrequested_grouping_cannot_replace_a_requested_global_total(tiny_caps):
    summary, index, _ = source()
    answer = ask("Records 시트 Amount 전체 합계는?", summary, index, grouped_plan(summary))
    assert_not_certified(answer)


def test_wrong_grouping_dimension_cannot_be_certified(tiny_caps):
    summary, index, _ = source()
    plan = grouped_plan(summary, group_by=["D"], order_by="B", limit=2)
    answer = ask("Records 시트 Department별 Amount 합계 상위 2개 보여줘", summary, index, plan)
    assert_not_certified(answer)


def test_requested_second_grouping_dimension_cannot_be_dropped(tiny_caps):
    summary, index, _ = source()
    plan = grouped_plan(summary, order_by="B", limit=2)
    answer = ask("Records 시트 Department와 State별 Amount 합계 상위 2개 보여줘", summary, index, plan)
    assert_not_certified(answer)


def test_group_ranking_requires_a_single_requested_statistic(tiny_caps):
    summary, index, _ = source()
    answer = ask("Records 시트 Department별 Amount 합계와 평균 상위 2개 보여줘", summary, index,
                 grouped_plan(summary, statistic="all", order_by="B", limit=2))
    assert_not_certified(answer)


@pytest.mark.parametrize("statistic", ["합계", "평균", "최솟값", "최댓값"])
def test_raw_top_n_list_cannot_replace_requested_top_n_aggregate(tiny_caps, statistic):
    summary, index, _ = source()
    answer = ask(f"Records 시트 Amount 상위 2개 {statistic} 알려줘", summary, index,
                 raw_plan(summary, columns=("B",)))
    assert_not_certified(answer)


@pytest.mark.parametrize("question", [
    "Records 시트 Department별 Amount 합계 100 이상인 그룹 상위 2개 보여줘",
    "Records 시트 각 그룹 Department별 Amount 상위 2개 합계 알려줘",
    "Records 시트 Department별 Amount 합계 비중 상위 2개 보여줘",
    "Records 시트 Department별 Amount 중앙값 상위 2개 보여줘",
])
def test_unsupported_group_operation_cannot_be_dropped(tiny_caps, question):
    summary, index, _ = source()
    assert_not_certified(ask(question, summary, index, grouped_plan(summary, order_by="B", limit=2)))
