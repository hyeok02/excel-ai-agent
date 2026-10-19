"""Raw row ranking executes only after checking every eligible source key."""
from dataclasses import replace

import pytest

from app.agent.query.tabular_execution import execute_tabular_query
from app.agent.query.workbook_source_models import SourceReadLimits
from tests.support.large_workbook_fixtures import (
    equal, offline, parsed, plan_for, tiny_caps, workbook,
)


def matrix():
    return [["Record", "Amount", "Group"],
            *[[f"Item{n}", n, "eligible"] for n in range(1, 10)],
            ["Tail", 999, "eligible"], ["Excluded", 9999, "excluded"]]


def ranking(summary, **updates):
    fields = dict(operation="row_list", columns=("A", "B"), order_by="B", limit=2)
    fields.update(updates)
    return plan_for(summary, **fields)


def test_tail_winner_is_ranked_after_filter_over_the_complete_source(tiny_caps):
    summary, index, _ = parsed(workbook({"Records": matrix()}))
    plan = ranking(summary, filters=(equal("C", "eligible"),))
    answer = execute_tabular_query(plan, summary, index,
                                  "Group이 eligible인 Amount 상위 2개 Record와 Amount 보여줘")
    assert answer is not None and answer.verification.level == "request_checked"
    assert "Record: Tail; Amount: 999" in answer.answer
    assert "Record: Item9; Amount: 9" in answer.answer
    assert "Excluded" not in answer.answer
    assert "full_source_scan" in answer.verification.checks


def test_source_bottom_n_retains_negative_tail_value(tiny_caps):
    rows = matrix()
    rows[-1][1] = -300
    summary, index, _ = parsed(workbook({"Records": rows}))
    plan = ranking(summary, descending=False)
    answer = execute_tabular_query(plan, summary, index, "Amount 하위 2개 Record와 Amount 보여줘")
    assert answer is not None
    assert "Record: Excluded; Amount: -300" in answer.answer and "Record: Item1; Amount: 1" in answer.answer
    assert "Record: Tail" not in answer.answer


@pytest.mark.parametrize("value", [None, "unknown", "=External!B2"])
def test_unknown_tail_order_value_cannot_be_dropped_to_certify_rank(tiny_caps, value):
    rows = matrix()
    rows[-1][1] = value
    summary, index, _ = parsed(workbook({"Records": rows}))
    assert execute_tabular_query(ranking(summary), summary, index,
                                "Amount 상위 2개 Record와 Amount 보여줘") is None


def test_unknown_filtered_out_order_value_does_not_block_known_population(tiny_caps):
    rows = matrix()
    rows[-1][1] = "=External!B2"
    summary, index, _ = parsed(workbook({"Records": rows}))
    answer = execute_tabular_query(ranking(summary, filters=(equal("C", "eligible"),)), summary, index,
                                  "Group이 eligible인 Amount 상위 2개 Record와 Amount 보여줘")
    assert answer is not None and "Record: Tail; Amount: 999" in answer.answer


def test_tail_format_difference_blocks_numeric_rank_even_if_not_a_winner(tiny_caps):
    book = workbook({"Records": matrix()})
    book.active["B12"] = 0.5
    book.active["B12"].number_format = "0%"
    summary, index, _ = parsed(book)
    assert execute_tabular_query(ranking(summary), summary, index,
                                "Amount 상위 2개 Record와 Amount 보여줘") is None


def test_budget_failure_or_missing_provider_never_certifies_prefix_top_n(tiny_caps):
    summary, index, _ = parsed(workbook({"Records": matrix()}), limits=SourceReadLimits(max_cells=10))
    question = "Amount 상위 2개 Record와 Amount 보여줘"
    assert execute_tabular_query(ranking(summary), summary, index, question) is None
    assert execute_tabular_query(ranking(summary), summary, replace(index, source_provider=None), question) is None


def test_complete_source_rank_cannot_reuse_a_sort_plan_for_wrong_direction(tiny_caps):
    summary, index, _ = parsed(workbook({"Records": matrix()}))
    assert execute_tabular_query(ranking(summary), summary, index,
                                "Amount 하위 2개 Record와 Amount 보여줘") is None
