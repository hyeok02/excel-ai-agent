"""End-to-end source extraction proves calendar filters before certifying."""
import pytest

from tests.support.trend_adversarial_fixtures import checked, direct, not_certified
from tests.tabular_query_fixtures import table_fixture


def source(values=(99, 10, 12, 9, 88), header="Total Employees"):
    dates = ["2024-03-31", "2024-04-30", "2024-05-31", "2024-06-30", "2024-07-31"]
    return table_fixture([(1, 1, [["Date", header], *map(list, zip(dates, values))])])


@pytest.mark.parametrize("phrase", [
    "2024년 2분기", "Q2 2024", "second quarter of 2024", "2024년도 2분기만",
    "only in Q2 2024", "in Q2 2024 only",
])
def test_quarter_excludes_outside_values_and_keeps_source_evidence(phrase):
    summary, index = source()
    answer = direct(summary, index, f"Total Employees {phrase} 추이를 설명해줘")
    checked(answer)
    assert "2024-04-30" in answer.answer and "2024-06-30" in answer.answer
    assert "2024-03-31" not in answer.answer and "2024-07-31" not in answer.answer
    assert "상승" in answer.answer and "하락" in answer.answer
    assert "달력 분기·반기 기준" in answer.answer


def test_invalid_value_outside_quarter_does_not_block_but_inside_still_does():
    summary, index = source(("unavailable", 10, 12, 9, "unavailable"))
    checked(direct(summary, index, "Total Employees 2024년 2분기 추이"))
    summary, index = source((99, 10, "unavailable", 9, 88))
    answer = direct(summary, index, "Total Employees 2024년 2분기 추이")
    not_certified(answer)
    assert answer.status == "insufficient_evidence"


def test_half_year_is_a_window_not_a_request_to_sum_observations():
    summary, index = source()
    answer = direct(summary, index, "Total Employees 2024년 상반기 추이")
    checked(answer)
    assert "2024-03-31" in answer.answer and "2024-06-30" in answer.answer
    assert "2024-07-31" not in answer.answer


def test_literal_quarter_name_and_independent_window_both_bind():
    summary, index = source(header="Q1 Employees")
    answer = direct(summary, index, "Q1 Employees 2024년 2분기 추이")
    checked(answer)
    assert "2024-04-30" in answer.answer and "2024-03-31" not in answer.answer
