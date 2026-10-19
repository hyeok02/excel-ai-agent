"""Horizontal report shapes obey the same chronological and scope rules."""
import pytest

from tests.support.large_workbook_fixtures import offline
from tests.support.trend_adversarial_fixtures import checked, direct, not_certified
from tests.tabular_query_fixtures import table_fixture


@pytest.mark.parametrize("order", [[0, 1, 2, 3], [3, 2, 1, 0], [2, 0, 3, 1]])
def test_horizontal_reversed_and_shuffled_series_show_rebound(order):
    dates = ["2024-03-31", "2024-06-30", "2024-09-30", "2024-12-31"]
    values = [100, 150, 120, 130]
    matrix = [["Metric", *[dates[number] for number in order]],
              ["Total Employees", *[values[number] for number in order]]]
    summary, index = table_fixture([(4, 3, matrix)])
    answer = direct(summary, index)
    checked(answer)
    assert "반등" in answer.answer and "하락" in answer.answer
    assert "150" in answer.answer and "120" in answer.answer


@pytest.mark.parametrize("date,value", [(None, 120), ("unknown", 120),
                                      ("2024-06-30", None), ("2024-06-30", "=OUTSIDE()")])
def test_horizontal_missing_middle_axis_or_metric_is_not_skipped(date, value):
    matrix = [["Metric", "2024-03-31", date, "2024-09-30"],
              ["Total Employees", 100, value, 110]]
    summary, index = table_fixture([(1, 1, matrix)])
    not_certified(direct(summary, index))


def test_disagreeing_horizontal_date_axes_are_not_arbitrarily_selected():
    matrix = [["Observation Date", "2024-03-31", "2024-06-30", "2024-09-30"],
              ["Effective Date", "2023-03-31", "2023-09-30", "2023-06-30"],
              ["Total Employees", 100, 120, 110]]
    summary, index = table_fixture([(1, 1, matrix)])
    not_certified(direct(summary, index))
