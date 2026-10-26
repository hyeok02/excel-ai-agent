"""Unfamiliar series preserve time order, rebound and source units."""
from itertools import permutations

import pytest

from app.services.insights.facts.horizontal_series import extract_horizontal_series
from app.services.insights.narratives.horizontal_trends import horizontal_trend_report
from app.services.insights.display.amount_units import amount_unit
from tests.test_horizontal_series import cell, region
from tests.test_insight_series_dimensions import _context, _report


def _source(order, values=(100, 60, 90), formats=None, label="Output"):
    dates = ("2024-01-01", "2024-06-01", "2025-01-01")
    formats = formats or ["General"] * 3
    return region([cell(f"{chr(66 + position)}1", dates[index]) for position, index in enumerate(order)],
                  [cell("A2", label), *[cell(f"{chr(66 + position)}2", values[index], formats[index])
                                        for position, index in enumerate(order)]])


def _horizontal(source, note=None):
    facts = {"horizontal_series": extract_horizontal_series([source])}
    if note:
        facts["table_regions"] = [{"rows": [[{"cell": "A6", "value": note}]]}]
    return horizontal_trend_report({"sheets": [{"name": "Factory", "business_facts": facts}]})


@pytest.mark.parametrize("order", list(permutations(range(3))))
def test_decline_then_rebound_is_invariant_to_horizontal_date_order(order):
    [insight], overview = _horizontal(_source(order))
    assert "100" in overview and "60" in overview and "90" in overview
    assert "감소한 뒤 반등" in overview
    assert insight.category == "change"  # Recommendations remain source-bounded endpoint questions.
    for column in "BCD":
        assert f"'Factory'!{column}2" in insight.evidence


def test_return_to_start_is_not_reported_as_a_monotonic_increase():
    [insight], overview = _horizontal(_source((0, 1, 2), (100, 60, 100)))
    assert "시작과 마지막 값이 같습니다" in overview
    assert "감소한 뒤 반등" in overview
    vertical = _context([("2024-01-01", "North", 100),
                         ("2024-06-01", "North", 60), ("2025-01-01", "North", 100)])
    result = _report(vertical)
    assert "감소한 뒤 반등" in result.insights[0].fact
    assert result.insights[0].validation_status.value == "verified"


@pytest.mark.parametrize("middle", [None, "#PEND", True])
def test_incomplete_horizontal_series_never_claims_a_complete_trend(middle):
    assert extract_horizontal_series([_source((0, 1, 2), (100, middle, 90))]) == []


def test_sheet_money_note_does_not_turn_headcount_into_money():
    [insight], _ = _horizontal(_source((0, 1, 2), label="Total Employees"), "in $ Millions")
    assert "100명" in insight.fact and "90명" in insight.fact
    assert "달러" not in insight.fact and "백만" not in insight.fact


def test_sheet_money_note_does_not_turn_growth_rates_into_money():
    [insight], _ = _horizontal(_source((0, 1, 2), label="Revenue Growth"), "in $ Millions")
    assert "달러" not in insight.fact and "백만" not in insight.fact


def test_magnitude_without_stated_currency_does_not_invent_dollars():
    result = amount_unit({"name": "Factory", "business_facts": {
        "table_regions": [{"rows": [[{"cell": "A1", "value": "in millions"}]]}],
    }})
    assert result[0] == "백만"


def test_explicit_person_units_do_not_translate_a_sales_role_into_revenue():
    [insight], _ = _horizontal(_source((0, 1, 2), (10, 6, 9), ['0"명"'] * 3, "Sales"))
    assert "Sales" in insight.fact and "매출" not in insight.fact


def test_duplicate_dates_require_equal_values_or_explicit_separate_bases():
    source = region([cell("B1", "2024-01-01"), cell("C1", "2024-01-01"), cell("D1", "2025-01-01")],
                    [cell("A2", "Output"), cell("B2", 100), cell("C2", 500), cell("D2", 600)])
    assert extract_horizontal_series([source]) == []
    separated = region([cell("B1", "Actual"), cell("D1", "Budget")],
                       [cell("B2", "2024-01-01"), cell("C2", "2025-01-01"),
                        cell("D2", "2024-01-01"), cell("E2", "2025-01-01")],
                       [cell("A3", "Output"), cell("B3", 100), cell("C3", 110), cell("D3", 500), cell("E3", 600)])
    series = extract_horizontal_series([separated])
    assert len(series) == 2 and {item["basis"] for item in series} == {"Actual", "Budget"}


def test_sampled_timeline_does_not_present_itself_as_all_periods():
    source = region([cell(f"{column}1", f"2025-0{month}-01") for month, column in enumerate("BCDEF", 1)],
                    [cell("A2", "Output"), *[cell(f"{column}2", value)
                                              for column, value in zip("BCDEF", (100, 110, 60, 120, 130))]])
    [insight], _ = _horizontal(source)
    assert "주요 시점의 기록" in insight.fact and "증가와 감소" in insight.fact
    assert "'Factory'!D2" in insight.evidence  # The omitted dip remains cited and used for the path.
    context = _context([(f"2025-0{month}-01", "North", value)
                        for month, value in enumerate((100, 110, 60, 120, 130), 1)])
    assert "주요 시점의 기록" in _report(context).insights[0].fact
