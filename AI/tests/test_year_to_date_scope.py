"""A YTD month window needs complete, same-metric monthly evidence for every year."""
import copy

import pytest

from app.services.insights.narratives.year_to_date_scope import year_to_date_scope
from tests.support.year_to_date_fixtures import _cell, _fixture, _scope


@pytest.mark.parametrize("month_count", [2, 5, 8, 12])
def test_complete_calendar_months_prove_variable_window_and_reference_every_input(month_count):
    fixture = _fixture(month_count)
    label, refs = _scope(fixture)
    assert label == f"(1~{month_count}월 누적)"
    assert "'Observations'!A1" in refs and "'Observations'!B1" in refs
    for _, _, heading, records, _ in fixture[1]:
        assert f"'Observations'!{heading['cell']}" in refs
        for _, axis, values in records:
            assert f"'Observations'!{axis['cell']}" in refs
            assert f"'Observations'!{values[2]['cell']}" in refs


def test_one_mismatched_year_prevents_a_shared_window_claim():
    fixture = _fixture()
    fixture[2][3][0][2][2]["value"] += 1
    assert _scope(fixture) == ("", [])


@pytest.mark.parametrize("break_kind", ["missing", "missing_value", "duplicate", "unit"])
def test_gaps_duplicate_months_missing_values_and_mixed_units_do_not_supply_scope(break_kind):
    fixture = _fixture()
    records = fixture[1][0][3]
    if break_kind == "missing":
        records.pop(2)
    elif break_kind == "missing_value":
        records[2][2][2]["value"] = None
    elif break_kind == "duplicate":
        records.append(copy.deepcopy(records[-1]))
    else:
        records[2][2][2]["number_format"] = '0 "kg"'
    assert _scope(fixture) == ("", [])


@pytest.mark.parametrize("section", ["Fiscal Year 2023", "Year 2023 rolling", "2023 Q1"])
def test_non_calendar_section_cannot_prove_a_calendar_ytd_window(section):
    fixture = _fixture()
    original = fixture[1][0]
    fixture[1][0] = (original[0], section, *original[2:])
    assert _scope(fixture) == ("", [])


@pytest.mark.parametrize("section", ["Rolling 12 Months", "Fiscal YTD", "Annual Totals"])
def test_non_ytd_sections_are_not_reinterpreted(section):
    sheet, series, target = _fixture()
    assert year_to_date_scope(sheet, section, 2, target[3], series=series) == ("", [])


def test_same_metric_name_in_a_different_table_cannot_supply_missing_months():
    fixture = _fixture()
    original = fixture[1][0]
    another_header = [_cell("A80", "Period"), _cell("B80", "Total output")]
    fixture[1][0] = (another_header, *original[1:])
    assert _scope(fixture) == ("", [])


def test_duplicate_monthly_blocks_are_not_chosen_arbitrarily():
    fixture = _fixture()
    fixture[1].insert(1, copy.deepcopy(fixture[1][0]))
    assert _scope(fixture) == ("", [])


def test_different_year_endpoints_do_not_become_one_shared_window():
    fixture = _fixture()
    fixture[2][3][0][2][2]["value"] = 1 + 2 + 3 + 4
    assert _scope(fixture) == ("", [])


def test_zero_values_cannot_prove_an_arbitrary_month_endpoint():
    fixture = _fixture()
    for entry in fixture[1]:
        for _, _, values in entry[3]:
            values[2]["value"] = 0
    assert _scope(fixture) == ("", [])


@pytest.mark.parametrize("metric,fmt", [("Average price", "General"), ("Occupancy", "0.0%")])
def test_rates_and_averages_are_not_summed_to_prove_a_ytd_window(metric, fmt):
    fixture = _fixture()
    for entry in fixture[1]:
        entry[0][1]["value"] = metric
        for _, _, values in entry[3]:
            values[2]["number_format"] = fmt
    assert _scope(fixture) == ("", [])


def test_a_later_zero_month_with_same_total_is_ambiguous():
    fixture = _fixture()
    for entry in fixture[1][:-1]:
        entry[3][-1][2][2]["value"] = 0
    for target, monthly in zip(fixture[2][3], fixture[1][:-1]):
        target[2][2]["value"] = sum(row[2][2]["value"] for row in monthly[3])
    assert _scope(fixture) == ("", [])


def test_year_sorting_and_integral_numeric_years_do_not_block_valid_scope():
    sheet, series, target = _fixture()
    for _, axis, _ in target[3]:
        axis["value"] = float(axis["value"])
    target[3].reverse()
    ordered = sorted(target[3], key=lambda row: row[0])
    label, _ = year_to_date_scope(sheet, target[1], 2, ordered, series=series)
    assert label == "(1~5월 누적)"


def test_a_missing_month_cannot_make_an_earlier_matching_prefix_look_complete():
    fixture = _fixture()
    for entry in fixture[1][:-1]:
        entry[3].pop(2)
    for target, monthly in zip(fixture[2][3], fixture[1][:-1]):
        target[2][2]["value"] = sum(row[2][2]["value"] for row in monthly[3][:2])
    assert _scope(fixture) == ("", [])
