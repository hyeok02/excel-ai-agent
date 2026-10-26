"""Independent endpoint oracles for ordinary tables, including row permutations."""
from itertools import permutations

import pytest

from app.services.insights.facts.business_facts import build_business_facts
from app.services.insights.models import WorkbookInsightReport
from app.services.insights.verification.validator import validate_workbook_insights


def _context(data, headers=("Date", "Company Name", "Revenue")):
    rows = [[{"address": f"{chr(65 + col)}{row}", "value": value,
              "number_format": "General"} for col, value in enumerate(values)]
            for row, values in enumerate([headers, *data], 1)]
    facts = build_business_facts("Ordinary", [{"preview_rows": rows}], [], 30)
    return {"sheets": [{"name": "Ordinary", "business_facts": facts}]}


def _report(context):
    return validate_workbook_insights(
        WorkbookInsightReport(overview="", insights=[], limitations=[]), context,
    )


def test_two_entities_never_become_one_certified_900_percent_increase():
    context = _context([("2024-01-01", "North", 100), ("2025-01-01", "South", 1000)])
    assert context["sheets"][0]["business_facts"]["numeric_changes"] == []
    report = _report(context)
    assert not any("900%" in item.fact or "증가했습니다" in item.fact for item in report.insights)


@pytest.mark.parametrize("order", list(permutations(range(4))))
def test_each_entity_retains_its_own_independent_arithmetic_in_every_row_order(order):
    data = [("2024-01-01", "North", 100), ("2025-01-01", "North", 90),
            ("2024-01-01", "South", 1000), ("2025-01-01", "South", 1300)]
    context = _context([data[index] for index in order])
    changes = context["sheets"][0]["business_facts"]["numeric_changes"]
    assert len(changes) == 2
    north = next(change for change in changes if "North" in change["metric"])
    south = next(change for change in changes if "South" in change["metric"])
    assert (north["earliest_value"], north["latest_value"], north["change"]) == (100, 90, -10)
    assert (south["earliest_value"], south["latest_value"], south["change"]) == (1000, 1300, 300)
    report = _report(context)
    assert report.insights and report.insights[0].validation_status.value == "verified"
    assert "South" in report.insights[0].fact and "1,300" in report.insights[0].fact


def test_date_column_can_move_without_changing_the_result():
    context = _context([("North", 100, "2024-01-01"), ("North", 90, "2025-01-01")],
                       ("Company Name", "Revenue", "Date"))
    [change] = context["sheets"][0]["business_facts"]["numeric_changes"]
    assert change["change"] == -10 and "North" in change["metric"]
