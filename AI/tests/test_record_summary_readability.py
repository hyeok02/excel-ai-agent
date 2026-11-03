"""Readable record summaries preserve raw metric identity and source grounding."""
import re

import pytest

from app.services.insights.models import InsightValidationStatus, WorkbookInsightReport
from app.services.insights.narratives.record_summary import record_summary_report
from app.services.insights.verification.validation_index import workbook_evidence_index
from app.services.insights.verification.validator import (
    _validate_insight,
    validate_workbook_insights,
)


def _cell(address, value, fmt="General"):
    return {"cell": address, "value": value, "number_format": fmt}


def _source(amount="TotalPrice", quantity="Qty", category="Category", labels=None, values=None):
    labels = labels or ["Alpha", "Alpha", "Alpha", "Beta", "Beta", "Beta"]
    values = values or [20, 30, 10, 20, 10, 10]
    rows = [[_cell("A1", "Record ID"), _cell("B1", category), _cell("C1", amount),
             _cell("D1", quantity), _cell("E1", "UnitPrice")]]
    rows += [[_cell(f"A{i}", f"Entry-{i}"), _cell(f"B{i}", label),
              _cell(f"C{i}", value), _cell(f"D{i}", i - 1), _cell(f"E{i}", 3)]
             for i, (label, value) in enumerate(zip(labels, values), 2)]
    return {"sheets": [{"name": "Records", "business_facts": {"table_regions": [
        {"rows": rows, "rows_complete": True},
    ]}}]}


def _rows(context):
    return context["sheets"][0]["business_facts"]["table_regions"][0]["rows"]


def _quoted(text, label):
    return any(f"{left}{label}{right}" in text
               for left, right in [("'", "'"), ('"', '"'), ("‘", "’"), ("“", "”")])


@pytest.mark.parametrize("amount", ["TotalPrice", "total_price", "Total Price", "TotalAmount"])
def test_amount_headers_are_readable_without_changing_metric_identity(amount):
    items, overview = record_summary_report(_source(amount=amount))
    amount_item = next(item for item in items if item.category == "metric" and item.topic == amount)
    assert "금액" in amount_item.title and "금액" in amount_item.fact
    assert "100" in amount_item.fact
    assert amount_item.topic == amount
    assert set(amount_item.evidence) == {
        "'Records'!C1", "'Records'!A2:A7", "'Records'!C2:C7",
        "'Records'!B1", "'Records'!B2:B7",  # quoted categories also need evidence
    }
    assert "금액" in overview


@pytest.mark.parametrize("quantity", ["Qty", "Quantity", "Units"])
def test_quantity_headers_are_readable_and_do_not_inherit_money_units(quantity):
    source = _source(quantity=quantity)
    rows = _rows(source)
    rows[0].append(_cell("F1", "Currency"))
    for i, row in enumerate(rows[1:], 2):
        row.append(_cell(f"F{i}", "EUR"))
    items, _ = record_summary_report(source)
    item = next(item for item in items if item.category == "metric" and item.topic == quantity)
    assert "수량" in item.title and "수량" in item.fact
    assert "21" in item.fact
    assert "EUR" not in item.fact
    assert "'Records'!D1" in item.evidence and "'Records'!D2:D7" in item.evidence
    assert "EUR" in next(item.fact for item in items if item.category == "metric" and item.topic == "TotalPrice")


def test_overview_combines_amount_and_quantity_without_repeating_record_count():
    items, overview = record_summary_report(_source())
    assert len(items) == 3
    assert "금액" in overview and "100" in overview
    assert "수량" in overview and "21" in overview
    assert len(re.findall(r"6\s*(?:건|개)", overview)) == 1
    assert "이(가)" not in overview
    assert "UnitPrice" not in overview


@pytest.mark.parametrize("category,display", [("Category", "분류"), ("Group", "그룹")])
def test_single_winner_uses_readable_group_label_and_quotes_the_original_value(category, display):
    items, _ = record_summary_report(_source(category=category))
    item = next(item for item in items if item.category == "summary")
    assert display in item.fact
    assert _quoted(item.fact, "Alpha")
    assert "60" in item.fact and "60%" in item.fact
    assert "각각" not in item.fact and "이(가)" not in item.fact
    assert "'Records'!B1" in item.evidence and "'Records'!B2:B7" in item.evidence


def test_tied_winners_preserve_both_categories_and_their_own_share():
    items, _ = record_summary_report(_source(values=[20, 20, 10, 20, 20, 10]))
    fact = next(item.fact for item in items if item.category == "summary")
    assert _quoted(fact, "Alpha") and _quoted(fact, "Beta")
    assert "50%" in fact and "100%" not in fact
    assert "이(가)" not in fact


def test_category_values_are_not_translated_as_financial_metrics():
    source = _source(labels=["Sales"] * 3 + ["Operations"] * 3)
    items, overview = record_summary_report(source)
    fact = next(item.fact for item in items if item.category == "summary")
    assert _quoted(fact, "Sales")
    assert "매출" not in fact and "매출" not in overview


def test_insurance_value_is_not_relabelled_as_sales():
    items, overview = record_summary_report(_source(amount="InsuredValue"))
    item = next(item for item in items if item.category == "metric" and item.topic == "InsuredValue")
    assert "보험가액" in item.title and "보험가액" in item.fact
    assert "100" in item.fact
    assert "매출" not in overview


def test_unknown_headers_and_category_values_remain_source_identifiable():
    source = _source(amount="ContributionAmount", labels=["Plan X"] * 3 + ["Plan Y"] * 3)
    items, _ = record_summary_report(source)
    item = next(item for item in items if item.category == "metric" and item.topic == "ContributionAmount")
    assert "ContributionAmount" in item.title or "ContributionAmount" in item.fact
    assert _quoted(next(item.fact for item in items if item.category == "summary"), "Plan X")


def test_no_currency_or_quantity_unit_is_invented_when_source_has_none():
    items, overview = record_summary_report(_source())
    text = " ".join([overview, *(item.fact for item in items)])
    assert not any(token in text for token in ["USD", "EUR", "$", "달러", "100원", "100 원", "21개", "21 개"])
    assert all(item.topic != "UnitPrice" for item in items)


@pytest.mark.parametrize("sheet,sales", [("RetailSales", True), ("Sales_Records", True),
                                      ("Purchases", False), ("SalesForecast", False),
                                      ("SalesDepartment", False), ("Data", False)])
def test_sales_context_requires_explicit_transaction_source(sheet, sales):
    source = _source()
    source["filename"] = "Sales.xlsx"  # Filenames do not supply business meaning.
    source["sheets"][0]["name"] = sheet
    items, overview = record_summary_report(source)
    assert ("판매 내역" in overview) is sales
    assert all(("판매 내역" in item.fact) is sales for item in items if item.category == "metric")


def test_sales_sheet_without_price_and_quantity_is_not_called_sales_records():
    source = _source(amount="EmployeeCount", quantity="Headcount")
    source["sheets"][0]["name"] = "Sales"
    _, overview = record_summary_report(source)
    assert "판매 내역" not in overview and "매출" not in overview


def test_distinct_source_columns_never_merge_into_one_display_label():
    source = _source(quantity="TotalAmount")
    items, overview = record_summary_report(source)
    metrics = [item for item in items if item.category == "metric"]
    assert len({item.title for item in metrics}) == 2
    assert "TotalPrice" in overview and "TotalAmount" in overview


def test_model_payload_cannot_skip_the_validated_context_policy():
    raw = WorkbookInsightReport.model_validate({
        "overview": "Untrusted summary", "insights": [], "_overview_has_context": True,
    })
    assert raw._overview_has_context is False
    assert "_overview_has_context" not in WorkbookInsightReport.model_json_schema()["properties"]


@pytest.mark.parametrize("failure", ["mixed_currency", "subtotal", "duplicate_key", "incomplete"])
def test_readability_does_not_enable_unsafe_record_totals(failure):
    source = _source()
    rows = _rows(source)
    if failure == "mixed_currency":
        rows[0].append(_cell("F1", "Currency"))
        for i, row in enumerate(rows[1:], 2):
            row.append(_cell(f"F{i}", "EUR" if i % 2 else "USD"))
    elif failure == "subtotal":
        rows[-1][1]["value"] = "Alpha Total"
    elif failure == "duplicate_key":
        rows[-1][0]["value"] = rows[-2][0]["value"]
    else:
        source["sheets"][0]["business_facts"]["table_regions"][0]["rows_complete"] = False
    assert not record_summary_report(source)[0]


def test_readable_canonical_report_is_verified_against_the_original_source():
    source = _source()
    items, _ = record_summary_report(source)
    report = validate_workbook_insights(WorkbookInsightReport(overview="", insights=[]), source)
    assert len(report.insights) == len(items) == 3
    assert report.validation.overview_validated
    assert all(item.validation_status == InsightValidationStatus.VERIFIED for item in report.insights)
    assert {item.fact for item in report.insights} == {item.fact for item in items}
    assert "금액" in report.overview and "수량" in report.overview
    assert "관련 내용을 정리한 자료" not in report.overview


@pytest.mark.parametrize("failure", ["fabricated_total", "missing_metric_evidence"])
def test_readable_wording_does_not_grant_verification_to_an_incorrect_claim(failure):
    source = _source()
    items, _ = record_summary_report(source)
    candidate = next(item for item in items if item.category == "metric" and item.topic == "TotalPrice")
    if failure == "fabricated_total":
        candidate = candidate.model_copy(update={"fact": candidate.fact.replace("100", "987,654")})
    else:
        candidate = candidate.model_copy(update={"evidence": ["'Records'!A2:A7"]})
    assert _validate_insight(candidate, workbook_evidence_index(source), items) is None
