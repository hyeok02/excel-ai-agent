"""Only dates known to be outside scope may bypass metric validation."""
from dataclasses import replace

import pytest

from tests.support.large_workbook_fixtures import offline
from tests.support.trend_adversarial_fixtures import direct
from tests.support.trend_scoped_fixtures import (
    QUESTION, VALID_ROWS, formats, period_checked, refused, series,
)


@pytest.mark.parametrize("layout", ["vertical", "horizontal"])
@pytest.mark.parametrize("invalid", [None, "unavailable", "=MISSING_CACHE()", True])
def test_known_outside_period_invalid_values_do_not_block_requested_history(layout, invalid):
    summary, index = series([["2023-12-31", invalid], *VALID_ROWS, ["2025-01-31", invalid]], layout)
    period_checked(direct(summary, index, QUESTION))


@pytest.mark.parametrize("layout", ["vertical", "horizontal"])
@pytest.mark.parametrize("invalid", [None, "unavailable", "=MISSING_CACHE()", True])
def test_same_invalid_values_inside_requested_history_remain_blocked(layout, invalid):
    rows = [VALID_ROWS[0], ["2024-02-29", invalid], VALID_ROWS[2]]
    summary, index = series(rows, layout)
    refused(direct(summary, index, QUESTION))


@pytest.mark.parametrize("layout", ["vertical", "horizontal"])
def test_conflicting_duplicate_outside_period_does_not_poison_selected_series(layout):
    rows = [["2023-12-31", 9], ["2023-12-31", 999], *VALID_ROWS]
    summary, index = series(rows, layout)
    period_checked(direct(summary, index, QUESTION))


@pytest.mark.parametrize("layout", ["vertical", "horizontal"])
def test_conflicting_duplicate_inside_period_is_never_silently_deduplicated(layout):
    summary, index = series([*VALID_ROWS, ["2024-02-29", 999]], layout)
    refused(direct(summary, index, QUESTION))


@pytest.mark.parametrize("layout", ["vertical", "horizontal"])
@pytest.mark.parametrize("outside", [True, False])
def test_unit_mismatch_is_scoped_by_original_date_not_by_value_position(layout, outside):
    summary, index = series([["2023-12-31", 0.5], *VALID_ROWS], layout)
    address = ("B2" if outside else "B4") if layout == "vertical" else ("B2" if outside else "D2")
    index = formats(summary, index, {address: "0.00%"})
    answer = direct(summary, index, QUESTION)
    period_checked(answer) if outside else refused(answer)


@pytest.mark.parametrize("layout", ["vertical", "horizontal"])
@pytest.mark.parametrize("unknown", [None, "unknown", "=MISSING_DATE()"])
def test_unknown_date_cannot_be_assumed_outside_requested_period(layout, unknown):
    summary, index = series([[unknown, 999], *VALID_ROWS], layout)
    refused(direct(summary, index, QUESTION))


@pytest.mark.parametrize("layout", ["vertical", "horizontal"])
def test_incomplete_original_read_cannot_prove_omitted_dates_are_outside_scope(layout):
    summary, index = series([["2023-12-31", 9], *VALID_ROWS], layout)
    index = replace(index, rows=index.rows[:-1], truncated=True,
                    truncated_sheet_names=frozenset({"Arbitrary"}))
    refused(direct(summary, index, QUESTION))


@pytest.mark.parametrize("layout", ["vertical", "horizontal"])
def test_original_date_mismatch_cannot_use_summary_date_to_drop_a_bad_value(layout):
    summary, index = series([["2024-04-30", None], *VALID_ROWS], layout)
    address = "A2" if layout == "vertical" else "B1"
    for row in summary.sheets[0].regions[0].analysis_rows:
        for cell in row:
            if cell["address"] == address:
                cell["value"] = "2023-12-31"
    refused(direct(summary, index, QUESTION))


@pytest.mark.parametrize("layout", ["vertical", "horizontal"])
def test_partial_original_even_with_all_requested_cells_present_remains_unverified(layout):
    summary, index = series([["2023-12-31", None], *VALID_ROWS], layout)
    missing = {"A2", "B2"} if layout == "vertical" else {"B1", "B2"}
    rows = tuple(replace(row, cells=tuple(cell for cell in row.cells if cell.address not in missing))
                 for row in index.rows)
    index = replace(index, rows=rows, truncated=True, truncated_sheet_names=frozenset({"Arbitrary"}))
    refused(direct(summary, index, QUESTION))


@pytest.mark.parametrize("company", ["Project2024", "Project 2024"])
def test_identifier_year_does_not_create_scope_that_hides_missing_history(company):
    from tests.tabular_query_fixtures import table_fixture
    rows = [["Date", "Total Employees", "Company"], ["2023-12-31", None, company],
            *[[date, value, company] for date, value in VALID_ROWS]]
    summary, index = table_fixture([(1, 1, rows)])
    refused(direct(summary, index, f"{company} 전체 직원 수의 기간별 추이를 설명해줘"))
    period_checked(direct(summary, index, f"{company} {QUESTION}"))


@pytest.mark.parametrize("layout", ["vertical", "horizontal"])
def test_period_first_validation_is_independent_of_column_order_and_table_position(layout):
    from tests.tabular_query_fixtures import table_fixture
    ordered = [["2023-12-31", None], *reversed(VALID_ROWS)]
    matrix = ([["Total Employees", "Date"], *[[value, date] for date, value in ordered]]
              if layout == "vertical" else
              [["Metric", *[date for date, _ in ordered]],
               ["Total Employees", *[value for _, value in ordered]]])
    summary, index = table_fixture([(9, 4, matrix)], sheet_name="Moved Source")
    period_checked(direct(summary, index, QUESTION))
