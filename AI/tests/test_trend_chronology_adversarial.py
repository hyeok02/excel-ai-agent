"""A complete time path is not interchangeable with endpoint comparison."""
import re

import pytest

from tests.support.large_workbook_fixtures import offline
from tests.support.trend_adversarial_fixtures import checked, direct, source, wrong_aggregation
from tests.tabular_query_fixtures import table_fixture


@pytest.mark.parametrize("order", [None, [3, 2, 1, 0], [2, 0, 3, 1]])
def test_trend_sorts_source_dates_and_reports_rebound_not_monotonic_growth(order):
    summary, index = source(order=order)
    answer = direct(summary, index)
    checked(answer)
    assert re.search("증가|상승", answer.answer), answer.model_dump()
    assert re.search("감소|하락", answer.answer), answer.model_dump()
    assert "반등" in answer.answer, answer.model_dump()
    assert all(str(value) in answer.answer for value in [100, 150, 120, 130])
    assert "9,000" not in answer.answer and "9000" not in answer.answer
    references = {item.reference for item in answer.evidence}
    assert {f"{column}{row}" for column in "AB" for row in range(2, 6)} <= references


def test_equal_endpoints_do_not_hide_intervening_rise_and_fall():
    summary, index = source([100, 150, 80, 100])
    answer = direct(summary, index)
    checked(answer)
    assert "150" in answer.answer and "80" in answer.answer
    assert re.search("증가|상승", answer.answer) and re.search("감소|하락", answer.answer)
    assert "반등" in answer.answer


def test_valid_but_wrong_model_aggregation_cannot_capture_a_trend_question():
    summary, index = source(order=[3, 2, 1, 0])
    answer = wrong_aggregation(summary, index)
    checked(answer)
    assert "반등" in answer.answer
    assert "Revenue" not in answer.answer and "36,006" not in answer.answer


def test_exact_duplicate_observations_are_not_conflicting_dates():
    matrix = [["Date", "Total Employees"], ["2024-03-31", 100],
              ["2024-06-30", 120], ["2024-06-30", 120], ["2024-09-30", 110]]
    summary, index = table_fixture([(1, 1, matrix)])
    answer = direct(summary, index)
    checked(answer)
    assert "120" in answer.answer and "110" in answer.answer


def test_exact_series_copies_do_not_invent_ambiguity():
    matrix = [["Date", "Total Employees"], ["2024-03-31", 100],
              ["2024-06-30", 120], ["2024-09-30", 110]]
    summary, index = table_fixture([(1, 1, matrix), (8, 1, matrix)])
    answer = direct(summary, index)
    checked(answer)
    assert "120" in answer.answer and "110" in answer.answer
