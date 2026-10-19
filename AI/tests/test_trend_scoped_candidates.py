"""Different source candidates need independent proof of their period scope."""
import pytest

from tests.support.large_workbook_fixtures import offline
from tests.support.trend_adversarial_fixtures import direct, not_certified
from tests.support.trend_scoped_fixtures import QUESTION, VALID_ROWS, period_checked
from tests.tabular_query_fixtures import table_fixture


def _matrix(rows, layout):
    return ([["Date", "Total Employees"], *rows] if layout == "vertical" else
            [["Metric", *[row[0] for row in rows]], ["Total Employees", *[row[1] for row in rows]]])


@pytest.mark.parametrize("layout", ["vertical", "horizontal"])
def test_known_outside_candidate_with_bad_values_does_not_block_selected_period(layout):
    earlier = [["2023-06-30", None], ["2023-09-30", "unavailable"], ["2023-12-31", 999]]
    summary, index = table_fixture([(1, 1, _matrix(VALID_ROWS, layout)),
                                    (9, 1, _matrix(earlier, layout))])
    period_checked(direct(summary, index, QUESTION))


@pytest.mark.parametrize("layout", ["vertical", "horizontal"])
def test_candidate_with_unknown_period_cannot_be_declared_irrelevant(layout):
    competing = [["2023-06-30", 700], [None, 999], ["2023-12-31", 800]]
    summary, index = table_fixture([(1, 1, _matrix(VALID_ROWS, layout)),
                                    (9, 1, _matrix(competing, layout))])
    not_certified(direct(summary, index, QUESTION))


@pytest.mark.parametrize("layout", ["vertical", "horizontal"])
def test_mixed_old_and_requested_competitor_cannot_be_ignored_on_its_first_date(layout):
    competing = [["2023-06-30", 700], ["2024-01-31", 999], ["2024-03-31", 800]]
    summary, index = table_fixture([(1, 1, _matrix(VALID_ROWS, layout)),
                                    (9, 1, _matrix(competing, layout))])
    not_certified(direct(summary, index, QUESTION))
