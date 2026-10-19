"""Original cells, units and metric roles remain distinct under trend routing."""
from dataclasses import replace

import pytest

from tests.support.large_workbook_fixtures import offline
from tests.support.trend_adversarial_fixtures import checked, direct, not_certified, source
from tests.tabular_query_fixtures import table_fixture


def _format_source(summary, index, formats):
    for region in summary.sheets[0].regions:
        for row in region.analysis_rows:
            for cell in row:
                if cell["address"] in formats:
                    cell["number_format"] = formats[cell["address"]]
    rows = tuple(replace(row, cells=tuple(
        replace(cell, number_format=formats.get(cell.address, cell.number_format))
        for cell in row.cells)) for row in index.rows)
    return replace(index, rows=rows)


@pytest.mark.parametrize("formats", [
    {"B2": "General", "B3": "0.00%", "B4": "General", "B5": "General"},
    {"B2": '"USD "0', "B3": '"USD "0', "B4": '"EUR "0', "B5": '"USD "0'},
    {"B2": "0", "B3": "0,", "B4": "0", "B5": "0"},
])
def test_changed_stored_or_display_unit_is_not_one_certified_series(formats):
    summary, index = source()
    index = _format_source(summary, index, formats)
    not_certified(direct(summary, index))


@pytest.mark.parametrize("address", ["A3", "B3", "B1"])
def test_summary_and_original_disagreement_cannot_certify_trend(address):
    summary, index = source()
    for row in summary.sheets[0].regions[0].analysis_rows:
        for cell in row:
            if cell["address"] == address:
                cell["value"] = "not-the-original" if address != "B3" else 999999
    not_certified(direct(summary, index))


def test_raw_headcount_is_not_confused_with_growth_or_per_employee_metrics():
    matrix = [["Date", "Total Employees", "Headcount Growth", "Revenue per Employee"],
              ["2024-03-31", 100, 0.15, 910], ["2024-06-30", 120, 0.20, 980],
              ["2024-09-30", 110, -0.08, 1050]]
    summary, index = table_fixture([(1, 1, matrix)])
    answer = direct(summary, index)
    checked(answer)
    assert "120" in answer.answer and "110" in answer.answer
    assert "980" not in answer.answer and "1,050" not in answer.answer


def test_same_filename_does_not_reuse_a_different_original_series():
    first_summary, first_index = source([100, 150, 120, 130])
    second_summary, second_index = source([700, 600, 500, 400])
    for summary, index, expected, forbidden in [
        (first_summary, first_index, "반등", "700"),
        (second_summary, second_index, "700", "반등"),
        (first_summary, first_index, "반등", "700"),
    ]:
        answer = direct(summary, index)
        checked(answer)
        assert expected in answer.answer and forbidden not in answer.answer
