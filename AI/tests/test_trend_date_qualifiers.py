"""Unsupported period fragments never acquire a full-history verified badge."""
from dataclasses import replace

import pytest

from app.agent.query.trend_date_bounds import parse_trend_date_bounds
from tests.support.trend_adversarial_fixtures import checked, direct, not_certified, source
from tests.support.trend_fixtures import observations


@pytest.mark.parametrize("question", [
    "Total Employees trend Q1",
    "Total Employees trend in June", "Total Employees trend June to September",
    "Total Employees trend between January and March", "Total Employees trend in 2024 June",
    "Total Employees trend over the last 1 year in June",
    "Total Employees trend fiscal year 2024", "FY2024 Total Employees trend",
])
def test_unresolved_date_qualifiers_cannot_certify_a_different_window(question):
    summary, index = source()
    answer = direct(summary, index, question)
    not_certified(answer)
    assert answer.status == "insufficient_evidence"


@pytest.mark.parametrize("question", [
    "2024 Total Employees quarterly trend",
    "Total Employees quarterly trend from June 2024 to December 2024",
    "Total Employees quarterly trend from June to December 2024",
])
def test_explicit_calendar_window_and_generic_cadence_still_work(question):
    summary, index = source()
    checked(direct(summary, index, question))


def test_source_defined_fiscal_year_labels_are_not_reinterpreted_as_calendar_years():
    items = observations([1, 2], dates=["2023-01-01", "2024-01-01"], grain="annual")
    items = [replace(item, period_cell=replace(item.period_cell, value=f"FY{item.period.year}"))
             for item in items]
    bounds, error = parse_trend_date_bounds("Metric trend FY2023 to FY2024", items)
    assert error is None and bounds.start.year == 2023 and bounds.end.year == 2024


def test_month_name_inside_actual_metric_is_not_a_calendar_constraint():
    items = observations([1, 2], dates=["2023-01-01", "2024-01-01"])
    items = [replace(item, label=replace(item.label, value="June Campaign Employees")) for item in items]
    bounds, error = parse_trend_date_bounds("June Campaign Employees trend", items)
    assert error is None and bounds.start is None and bounds.end is None
