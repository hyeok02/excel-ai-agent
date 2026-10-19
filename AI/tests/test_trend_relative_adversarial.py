"""Rolling periods exclude old metric errors, never erase real identities."""
import pytest

from tests.support.large_workbook_fixtures import offline
from tests.support.trend_adversarial_fixtures import checked, direct, not_certified
from tests.support.trend_scoped_fixtures import normalize_formulas
from tests.tabular_query_fixtures import table_fixture

QUESTION = "최근 1년 Total Employees와 Temporary Employees의 기간별 추이를 비교해줘"


@pytest.mark.parametrize("placeholder", ["unavailable", "#PEND", "=EXTERNAL_DATA()"])
def test_old_invalid_other_metric_is_not_a_population_for_relative_anchor(placeholder):
    matrix = [["Date", "Total Employees", "Temporary Employees"],
              ["2022-12-31", 50, placeholder], ["2024-01-31", 100, 10],
              ["2024-02-29", 150, 20], ["2024-03-31", 120, 50]]
    summary, index = table_fixture([(1, 1, matrix)])
    normalize_formulas(summary)
    answer = direct(summary, index, QUESTION)
    checked(answer)
    assert "compare_trend_series" in answer.selected_tools
    assert answer.answer.count("3개 관측값") == 2
    assert "2022-12-31" not in answer.answer
    assert "2024-03-31" in answer.answer and "오늘이 아닌" in answer.answer


@pytest.mark.parametrize("placeholder", ["unavailable", "#PEND", "=EXTERNAL_DATA()"])
def test_relative_scope_keeps_invalid_requested_metric_inside_window_unverified(placeholder):
    matrix = [["Date", "Total Employees", "Temporary Employees"],
              ["2024-01-31", 100, 10], ["2024-02-29", 150, placeholder],
              ["2024-03-31", 120, 50]]
    summary, index = table_fixture([(1, 1, matrix)])
    normalize_formulas(summary)
    not_certified(direct(summary, index, QUESTION))


@pytest.mark.parametrize("header,identities", [
    ("Employee ID", [1, 2, 2, 2]), ("Company", ["Beta", "Alpha", "Alpha", "Alpha"]),
    ("Currency", ["EUR", "USD", "USD", "USD"]),
    ("Scenario", ["Estimate", "Actual", "Actual", "Actual"]),
])
def test_other_numeric_metrics_do_not_remove_real_relative_anchor_scope(header, identities):
    rows = [["2022-12-31", 50, 5], ["2024-01-31", 100, 10],
            ["2024-02-29", 150, 20], ["2024-03-31", 120, 50]]
    matrix = [["Date", "Total Employees", "Temporary Employees", header],
              *[[*row, identity] for row, identity in zip(rows, identities)]]
    summary, index = table_fixture([(1, 1, matrix)])
    not_certified(direct(summary, index, QUESTION))
