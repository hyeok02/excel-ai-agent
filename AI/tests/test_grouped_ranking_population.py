"""Whole-table ranking must operate on source rows, never its prefix samples."""
import pytest

from tests.support.grouped_ranking_fixtures import (
    assert_before, grouped_plan, line_with, raw_plan, source,
)
from tests.support.large_workbook_fixtures import (
    ask, assert_stream_checked, equal, fresh_index, offline, parsed, tiny_caps, workbook,
)


def test_filtered_top_rows_apply_predicate_before_ranking(tiny_caps):
    summary, index, _ = source()
    plan = raw_plan(summary, filters=[equal("D", "active")])
    answer = ask("Records 시트 State가 active인 Amount 상위 2개 Record와 Amount 보여줘",
                 summary, index, plan)
    assert_stream_checked(answer)
    assert_before(answer, "Tail", "Third")
    assert "70" in line_with(answer, "Tail") and "15" in line_with(answer, "Third")
    assert "Winner" not in answer.answer and "Fourth" not in answer.answer


@pytest.mark.parametrize("descending,question,expected", [
    (False, "하위", ["Late", "Low", "Seventh"]),
    (True, "상위", ["Winner", "Tail", "Third"]),
])
def test_signed_order_and_source_order_ties(tiny_caps, descending, question, expected):
    summary, index, _ = source()
    plan = raw_plan(summary, descending=descending, limit=3)
    answer = ask(f"Records 시트 Amount {question} 3개 Record와 Amount 보여줘", summary, index, plan)
    assert_stream_checked(answer)
    assert_before(answer, expected[0], expected[1])
    assert_before(answer, expected[1], expected[2])
    assert "Fourth" not in answer.answer


def test_group_totals_are_not_top_raw_rows(tiny_caps):
    summary, index, _ = source()
    plan = grouped_plan(summary, order_by="B", limit=3)
    answer = ask("Records 시트 Department별 Amount 합계 상위 3개 보여줘", summary, index, plan)
    assert_stream_checked(answer)
    assert_before(answer, "Delta", "Beta")
    assert_before(answer, "Beta", "Alpha")
    assert "970" in line_with(answer, "Delta")
    assert "24" in line_with(answer, "Beta")
    assert "16" in line_with(answer, "Alpha")


def test_group_totals_with_filters_include_tail_categories(tiny_caps):
    summary, index, _ = source()
    plan = grouped_plan(summary, filters=[equal("D", "active")], order_by="B", limit=2)
    answer = ask("Records 시트 State가 active인 Department별 Amount 합계 상위 2개 보여줘",
                 summary, index, plan)
    assert_stream_checked(answer)
    assert_before(answer, "Delta", "Alpha")
    assert "70" in line_with(answer, "Delta") and "24" in line_with(answer, "Alpha")
    assert "Gamma" not in answer.answer and "Beta" not in answer.answer


def test_group_count_ranking_does_not_need_a_numeric_measure(tiny_caps):
    summary, index, _ = source()
    plan = grouped_plan(summary, operation="row_count", columns=(), limit=2)
    answer = ask("Records 시트 Department별 행 개수 상위 2개 보여줘", summary, index, plan)
    assert_stream_checked(answer)
    assert_before(answer, "Alpha", "Beta")
    assert "3" in line_with(answer, "Alpha") and "3" in line_with(answer, "Beta")
    assert "Delta" not in answer.answer


def test_mean_is_accumulated_from_all_group_members_not_sample_means(tiny_caps):
    matrix = [["Record", "Amount", "Department"], ["A", 0, "Alpha"],
              ["B", 0, "Alpha"], ["C", 30, "Alpha"], ["D", 12, "Beta"]]
    summary, index, _ = source(matrix)
    plan = grouped_plan(summary, statistic="average", order_by="B", limit=2)
    answer = ask("Records 시트 Department별 Amount 평균 상위 2개 보여줘", summary, index, plan)
    assert_stream_checked(answer)
    assert_before(answer, "Beta", "Alpha")
    assert "평균 10" in line_with(answer, "Alpha")
    assert "평균 12" in line_with(answer, "Beta")


@pytest.fixture(scope="module")
def beyond_real_row_limit():
    matrix = [["Record", "Amount", "Department"]]
    matrix.extend([f"Item{n}", 1, "ordinary"] for n in range(1, 10_002))
    matrix.append(["TailWinner", 20_000, "tail-only"])
    return parsed(workbook({"Records": matrix}))


@pytest.mark.parametrize("grouped", [False, True])
def test_actual_ten_thousand_row_limit_cannot_hide_the_winner(beyond_real_row_limit, grouped):
    summary, _, content = beyond_real_row_limit
    index = fresh_index(summary, content)
    assert index.truncated_for({"Records"})
    plan = grouped_plan(summary, order_by="B", limit=1) if grouped else raw_plan(summary, limit=1)
    question = ("Records 시트 Department별 Amount 합계 상위 1개 보여줘" if grouped else
                "Records 시트 Amount 상위 1개 Record와 Amount 보여줘")
    answer = ask(question, summary, index, plan)
    assert_stream_checked(answer)
    assert ("tail-only" if grouped else "TailWinner") in answer.answer
    assert "20,000" in answer.answer
    assert any("10003" in item.reference for item in answer.evidence)
