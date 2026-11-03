"""Date roles and contextual wording require their original source evidence."""
import pytest

from app.services.insights.models import InsightValidationStatus, WorkbookInsightReport
from app.services.insights.narratives.record_summary import record_summary_report
from app.services.insights.verification.validation_index import workbook_evidence_index
from app.services.insights.verification.validator import _validate_insight, validate_workbook_insights
from tests.support.record_context_fixtures import _metric, _notes, _records
from tests.support.record_summary_fixtures import _cell, _rows


@pytest.mark.parametrize("date_header", ["Expiry", "Expiration Date", "만료일"])
def test_expiration_dates_are_not_reported_as_the_sales_period(date_header):
    source = _records(date_header=date_header)
    items, overview = record_summary_report(source)
    assert "판매 내역" in overview and "100" in overview
    assert "2023년" not in overview and "2024년" not in overview
    assert "'BookSales'!F2:F7" not in _metric(items).evidence


def test_month_precision_is_not_expanded_into_invented_calendar_days():
    source = _records(dates=["Jan 2024", "Feb 2024", "Mar 2024",
                             "Apr 2024", "May 2024", "Jun 2024"])
    items, overview = record_summary_report(source)
    assert items and "판매금액" in overview
    assert "1일" not in overview and "31일" not in overview
    assert "'BookSales'!F2:F7" not in _metric(items).evidence


def test_two_transaction_date_roles_do_not_choose_an_arbitrary_period():
    source = _records()
    rows = _rows(source)
    rows[0].append(_cell("G1", "OrderDate"))
    for i, row in enumerate(rows[1:], 2):
        row.append(_cell(f"G{i}", f"2025-08-{i:02d}"))
    items, overview = record_summary_report(source)
    assert items and "100" in overview
    assert not any(year in overview for year in ["2023년", "2024년", "2025년"])


@pytest.mark.parametrize("bad_date", [None, "not a date", "2024-02-31"])
def test_incomplete_or_invalid_dates_only_remove_period_not_the_totals(bad_date):
    source = _records()
    _rows(source)[3][-1]["value"] = bad_date
    items, overview = record_summary_report(source)
    assert items and "100" in overview and "판매금액" in overview
    assert "2023년" not in overview and "2024년" not in overview


def test_contextual_canonical_report_remains_verified_with_original_date_evidence():
    source = _records()
    items, _ = record_summary_report(source)
    report = validate_workbook_insights(WorkbookInsightReport(overview="", insights=[]), source)
    assert len(report.insights) == len(items) == 3
    assert report.validation.overview_validated
    assert all(item.validation_status == InsightValidationStatus.VERIFIED for item in report.insights)
    assert "도서 판매 내역" in report.overview and "2023년 11월 19일" in report.overview


def test_changing_period_to_a_date_absent_from_the_source_is_not_verified():
    source = _records()
    items, _ = record_summary_report(source)
    item = _metric(items)
    changed = item.model_copy(update={"fact": item.fact.replace("2023년", "2099년")})
    assert _validate_insight(changed, workbook_evidence_index(source), items) is None


@pytest.mark.parametrize("missing_reference", ["'Guide'!C2", "'Data'!F2:F7"])
def test_context_claims_cannot_keep_verification_without_their_source_evidence(missing_reference):
    source = _records("Data")
    _notes(source, "Data: Sales order records from a fictional furniture company")
    items, _ = record_summary_report(source)
    item = _metric(items)
    index = workbook_evidence_index(source)
    assert _validate_insight(item, index, items) is not None
    assert missing_reference in item.evidence
    changed = item.model_copy(update={
        "evidence": [ref for ref in item.evidence if ref != missing_reference],
    })
    assert _validate_insight(changed, index, items) is None


def test_a_different_product_subject_cannot_inherit_canonical_verification():
    source = _records("Data")
    _notes(source, "Data: Sales order records from a fictional furniture company")
    items, _ = record_summary_report(source)
    item = _metric(items)
    index = workbook_evidence_index(source)
    assert "가구 판매 내역" in item.fact
    assert _validate_insight(item, index, items) is not None
    changed = item.model_copy(update={"fact": item.fact.replace("가구 판매 내역", "의류 판매 내역")})
    assert _validate_insight(changed, index, items) is None
