"""Regressions use generic structures, not downloaded filenames or labels."""
import pytest

from app.services.insights.models import WorkbookInsight, WorkbookInsightReport
from app.services.insights.narratives.narrative_values import number
from app.services.insights.narratives.numeric_table_narratives import numeric_table_report
from app.services.insights.narratives.record_display import display_value
from app.services.insights.narratives.snapshot_narratives import snapshot_report
from app.services.insights.verification.validator import validate_workbook_insights
from app.services.insights.verification.validation_index import workbook_evidence_index
from app.services.insights.verification.relation_grounding import grounded_metric_owner


def cell(address, value, fmt="General"):
    return {"cell": address, "value": value, "number_format": fmt}


def source(rows, title=None, title_cell=None):
    return {"sheets": [{"name": "Input", "business_facts": {"table_regions": [{
        "rows": rows, "title": title, "title_cell": title_cell,
        "rows_complete": True,
    }]}}]}


@pytest.mark.parametrize("value,expected", [(1618.5, "1,618.5"), (-2400.75, "-2,400.75"),
                                           (0.001234, "0.001234"), (1500, "1,500")])
def test_fractional_values_do_not_disappear_at_magnitude_boundary(value, expected):
    assert number(value) == expected


def test_scientific_notation_does_not_gain_integer_rounding_tolerance():
    from decimal import Decimal
    from app.services.insights.verification.numeric_validation import unmatched_numbers
    assert unmatched_numbers("1e-6", {Decimal("0.17")}) == {"1e-6"}
    assert not unmatched_numbers("1.23e-6", {Decimal("0.000001234")})


def test_named_months_are_sorted_chronologically_not_alphabetically():
    from app.services.insights.facts.fact_trends import date_value, numeric_changes
    from app.services.insights.narratives.trend_narratives import trend_report
    records = [{"location": f"Input!A{row}:B{row}", "values": [
        cell(f"A{row}", date), {**cell(f"B{row}", value), "label": "Reading"},
    ]} for row, date, value in [(2, "2024 DEC", 90), (3, "2024 JAN", 100), (4, "2024 JUN", 80)]]
    changes = numeric_changes(records)
    assert changes[0]["earliest_period"] == "2024 JAN"
    assert changes[0]["latest_period"] == "2024 DEC"
    context = {"sheets": [{"name": "Input", "business_facts": {"time_series": records, "numeric_changes": changes}}]}
    items, _ = trend_report(context)
    assert "2024년 1월 100" in items[0].fact
    assert "2024년 12월 90" in items[0].fact
    assert "2024년 6월 80" in items[0].fact
    assert date_value("2024") is None


def test_snapshot_only_uses_standalone_caption_as_owner():
    rows = [[cell("A2", "Volume"), cell("B2", 120), cell("C2", 110)],
            [cell("A3", "Units"), cell("B3", 4200.5)],
            [cell("A4", "Price"), cell("B4", 7.75)],
            [cell("A5", "Options"), cell("B5", 12)]]
    context = source(rows, "Volume", rows[0][0])
    report = validate_workbook_insights(WorkbookInsightReport(overview="", insights=[]), context)
    assert report.insights
    assert "Volume의" not in report.overview
    assert "4,200.5" in report.overview

    rows.insert(0, [cell("A1", "Model inputs")])
    items, _ = snapshot_report(source(rows, "Model inputs", rows[0][0]))
    assert items[0].fact.startswith("Model inputs의 주요 수치")
    assert "'Input'!A1" in items[0].evidence


def test_canonical_shortcut_does_not_authorize_metric_as_owner():
    rows = [[cell("A2", "Volume"), cell("B2", 120)],
            [cell("A3", "Units"), cell("B3", 4200)],
            [cell("A4", "Price"), cell("B4", 7.75)]]
    context = source(rows)
    evidence = ["'Input'!A2:B4"]
    bad = WorkbookInsight(title="Volume", fact="Volume의 주요 수치는 Units 4,200, Price 7.75입니다.",
                          category="metric", severity="info", evidence=evidence, confidence=1)
    index = workbook_evidence_index(context)
    assert not grounded_metric_owner(bad.fact, {"input!a2:b4"}, index.observations)
    from app.services.insights.verification.validator import _validate_insight
    assert _validate_insight(bad, index, [bad]) is None
    valid = bad.model_copy(update={"fact": "Units 4,200, Price 7.75입니다."})
    assert _validate_insight(valid, index) is not None


def test_snapshot_percent_and_multiple_keep_distinct_units():
    rows = [[cell("A2", "Units"), cell("B2", 1000)],
            [cell("A3", "Price"), cell("B3", 17.5)],
            [cell("A4", "Options"), cell("B4", 50)],
            [cell("A5", "Effective rate"), cell("B5", 0.175, "0.00%")],
            [cell("A6", "Multiple ratio"), cell("B6", 1.71, "0.00")]]
    items, _ = snapshot_report(source(rows))
    assert "Effective rate 17.5%" in items[1].fact
    assert "Multiple ratio 1.71" in items[1].fact
    assert "Multiple ratio 171%" not in items[1].fact
    assert display_value(cell("A1", 17.5, '0.0"%"')) == "17.5%"


def numeric_context():
    rows = [[cell("A1", "Category"), cell("B1", "Reading")],
            [cell("A2", "West"), cell("B2", 1200.5)],
            [cell("A3", "East"), cell("B3", 32.25)],
            [cell("A4", "West"), cell("B4", 90)]]
    context = source(rows[1:])
    context["sheets"][0]["business_facts"]["table_regions"].insert(0, {"rows": rows[:1], "rows_complete": True})
    context["sheets"][0]["column_schema_samples"] = [{
        "column": "B", "display_name": "Reading", "header_path": ["Reading"],
        "source_range": "A1:B4", "data_type": "number", "standard_field": "metric",
    }]
    return context


def test_complete_numeric_table_has_literal_source_bound_summary():
    context = numeric_context()
    items, _ = numeric_table_report(context)
    assert len(items) == 1
    assert "3개 값" in items[0].fact
    assert "32.25~1,200.5" in items[0].fact
    assert "'Input'!B1" in items[0].evidence
    assert "'Input'!B2:B4" in items[0].evidence
    report = validate_workbook_insights(WorkbookInsightReport(overview="", insights=[]), context)
    assert report.validation.verified_count >= 1
    assert not report.overview.startswith("이 파일은 West")


@pytest.mark.parametrize("failure", ["partial", "wrong_header", "mixed", "foreign_range"])
def test_numeric_fallback_does_not_guess_incomplete_or_unbound_column(failure):
    context = numeric_context()
    sheet = context["sheets"][0]
    region = sheet["business_facts"]["table_regions"][1]
    if failure == "partial":
        region["rows_complete"] = False
    elif failure == "wrong_header":
        sheet["column_schema_samples"][0]["header_path"] = ["Unrelated"]
    elif failure == "mixed":
        region["rows"][0][1]["value"] = "#PEND"
    else:
        sheet["column_schema_samples"][0]["source_range"] = "D10:F40"
    assert numeric_table_report(context) == ([], "")
