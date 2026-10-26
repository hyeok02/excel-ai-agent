"""No false trend certification from conflicting dates, missing values or units."""
import pytest

from tests.test_insight_series_dimensions import _context, _report
from app.services.insights.facts.fact_trends import numeric_changes


def _records(values, formats=None, dates=None, label="Margin"):
    dates = dates or ["2024-01-01", "2024-06-01", "2025-01-01"][:len(values)]
    formats = formats or ["General"] * len(values)
    return [{"location": f"Data!A{index}:B{index}", "values": [
        {"cell": f"A{index}", "value": day},
        {"cell": f"B{index}", "label": label, "value": value, "number_format": fmt},
    ]} for index, (day, value, fmt) in enumerate(zip(dates, values, formats), 2)]


@pytest.mark.parametrize("middle", [None, "#PEND", "unknown", True, float("inf")])
def test_invalid_middle_value_is_not_silently_skipped(middle):
    assert numeric_changes(_records([100, middle, 80])) == []


@pytest.mark.parametrize("middle", [None, "#PEND", "unknown", True])
def test_missing_or_error_value_survives_table_extraction(middle):
    context = _context([("2024-01-01", "North", 100),
                        ("2024-06-01", "North", middle), ("2025-01-01", "North", 80)])
    assert context["sheets"][0]["business_facts"]["numeric_changes"] == []
    assert not any("감소세" in item.fact for item in _report(context).insights)


def test_conflicting_duplicate_date_is_not_arbitrarily_selected():
    assert numeric_changes(_records([100, 99, 150], dates=["2024-01-01", "2024-01-01", "2025-01-01"])) == []
    [change] = numeric_changes(_records([100, 100, 150], dates=["2024-01-01", "2024-01-01", "2025-01-01"]))
    assert change["change"] == 50


def test_duplicate_metric_header_is_not_overwritten():
    records = _records([100, 150])
    for record in records:
        record["values"].append({"label": "Margin", "value": 700})
    assert numeric_changes(records) == []


@pytest.mark.parametrize("formats", [('0" USD"', '0" KRW"'), ('0.0%', 'General'), (r'0\명', r'0\원')])
def test_different_units_cannot_be_certified_as_growth(formats):
    assert numeric_changes(_records([100, 150], formats)) == []


def test_percentage_cells_are_compared_in_percentage_points_not_raw_fractions():
    [change] = numeric_changes(_records([.2, 30], ['0.0%', '0.0"%"']))
    assert (change["earliest_value"], change["latest_value"], change["change"], change["unit"]) == (20, 30, 10, "%")


def test_scaled_money_formats_do_not_inflate_literal_units():
    [change] = numeric_changes(_records([1000, 1500], ['0,"천원"', '0,"천원"']))
    assert (change["earliest_value"], change["latest_value"], change["change"]) == (1, 1.5, .5)


def test_unstated_currency_scale_is_explicit_and_mixed_scales_are_not_compared():
    [change] = numeric_changes(_records([1000000, 1500000], ['0,,"USD"', '0,,"USD"']))
    assert change["unit"] == "백만 USD" and change["change"] == .5
    assert numeric_changes(_records([1000000, 1500000], ['0,,"USD"', '0"USD"'])) == []


@pytest.mark.parametrize("fmt,expected", [('£#,##0', "GBP"), ('¥#,##0', "¥"), ('0"JPY"', "JPY")])
def test_non_dollar_currencies_preserve_their_own_unit(fmt, expected):
    [change] = numeric_changes(_records([100, 150], [fmt, fmt]))
    assert change["unit"] == expected and change["change"] == 50
    assert numeric_changes(_records([100, 150], ['£#,##0', '¥#,##0'])) == []


def test_equivalent_date_spellings_cannot_hide_conflicts():
    assert numeric_changes(_records([100, 110, 150], dates=["2024-01-01", "2024-01-01T00:00:00", "2025-01-01"])) == []


def test_changing_explicit_notes_does_not_split_a_valid_subject_series():
    context = _context([("2024-01-01", "North", 100, "launched"),
                        ("2025-01-01", "North", 120, "campaign")],
                       ("Date", "Company Name", "Revenue", "Notes"))
    [change] = context["sheets"][0]["business_facts"]["numeric_changes"]
    assert change["change"] == 20 and "North" in change["metric"]
