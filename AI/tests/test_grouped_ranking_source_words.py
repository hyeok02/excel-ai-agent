"""Business source labels are not natural-language aggregation operators."""
import pytest

from tests.support.grouped_ranking_fixtures import grouped_plan, raw_plan, records, source
from tests.support.large_workbook_fixtures import (
    ask, assert_not_certified, assert_stream_checked, equal, offline, tiny_caps,
)


@pytest.mark.parametrize("label", ["Total Employees", "Average Cost", "Minimum Bid", "합계 금액"])
def test_source_metric_words_do_not_turn_row_ranking_into_aggregation(tiny_caps, label):
    matrix = records()
    matrix[0][1] = label
    summary, index, _ = source(matrix)
    question = f"Records 시트 {label} 상위 2개 Record와 {label} 보여줘"
    answer = ask(question, summary, index, raw_plan(summary))
    assert_stream_checked(answer)
    assert "Winner" in answer.answer and "Tail" in answer.answer


@pytest.mark.parametrize("label", ["Total Employees", "Average Cost"])
def test_group_mean_of_source_label_total_is_not_mistaken_for_two_statistics(tiny_caps, label):
    matrix = records()
    matrix[0][1] = label
    summary, index, _ = source(matrix)
    answer = ask(f"Records 시트 Department별 {label} 평균 상위 2개 보여줘", summary, index,
                 grouped_plan(summary, statistic="average", order_by="B", limit=2))
    assert_stream_checked(answer)
    assert "평균 485" in answer.answer and "평균 8" in answer.answer


def test_real_aggregate_after_statistic_named_header_is_still_required(tiny_caps):
    matrix = records()
    matrix[0][1] = "Total Employees"
    summary, index, _ = source(matrix)
    answer = ask("Records 시트 Total Employees 상위 2개 합계 알려줘", summary, index,
                 raw_plan(summary, columns=("B",)))
    assert_not_certified(answer)


@pytest.mark.parametrize("value", ["total", "average"])
def test_quoted_source_filter_value_is_not_a_statistic_operator(tiny_caps, value):
    matrix = records()
    matrix[-1][3] = value
    summary, index, _ = source(matrix)
    answer = ask(f"Records 시트 State가 '{value}'인 Amount 상위 2개 Record와 Amount 보여줘",
                 summary, index, raw_plan(summary, filters=[equal("D", value)]))
    assert_stream_checked(answer)
    assert "Tail" in answer.answer and "Winner" not in answer.answer


def test_standalone_statistic_header_cannot_mask_a_real_aggregate_request(tiny_caps):
    matrix = records()
    matrix[0][3] = "합계"
    summary, index, _ = source(matrix)
    answer = ask("Records 시트 Amount 상위 2개 합계 알려줘", summary, index,
                 raw_plan(summary, columns=("B", "D")))
    assert_not_certified(answer)
