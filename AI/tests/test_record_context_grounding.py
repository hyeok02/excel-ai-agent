"""Business context must belong to the selected records and their date role."""
import pytest

from app.services.insights.models import InsightValidationStatus, WorkbookInsightReport
from app.services.insights.narratives.record_summary import record_summary_report
from app.services.insights.verification.validation_index import workbook_evidence_index
from app.services.insights.verification.validator import _validate_insight, validate_workbook_insights
from tests.test_record_summary_readability import _cell, _rows, _source


def _records(name="BookSales", date_header="Date", dates=None):
    source = _source()
    source["filename"] = "irrelevant_insurance_forecast.xlsx"
    source["sheets"][0]["name"] = name
    rows = _rows(source)
    rows[0].append(_cell("F1", date_header))
    dates = dates or ["2024-03-04", "2023-11-19", "2024-01-08",
                      "2024-06-12", "2023-12-25", "2024-02-18"]
    for i, (row, date) in enumerate(zip(rows[1:], dates), 2):
        row.append(_cell(f"F{i}", date, "yyyy-mm-dd"))
    return source


def _notes(source, *texts):
    rows = [[_cell(f"C{i}", text)] for i, text in enumerate(texts, 2)]
    source["sheets"].append({
        "name": "Guide",
        "business_facts": {"table_regions": [{"rows": rows, "rows_complete": True}]},
    })


def _metric(items, topic="TotalPrice"):
    return next(item for item in items if item.category == "metric" and item.topic == topic)


def test_book_sales_context_uses_source_subject_and_chronological_date_extent():
    source = _records()
    items, overview = record_summary_report(source)
    assert "도서 판매 내역" in overview
    assert "판매금액" in overview and "100" in overview
    assert "판매수량" in overview and "21" in overview
    assert "2023년 11월 19일" in overview and "2024년 6월 12일" in overview
    assert overview.index("2023년 11월 19일") < overview.index("2024년 6월 12일")
    assert "보험" not in overview and "예측" not in overview
    assert {"'BookSales'!F1", "'BookSales'!F2:F7"} <= set(_metric(items).evidence)


def test_korean_purchase_headers_preserve_purchase_meaning():
    source = _records("전자제품 구매", "구매일")
    rows = _rows(source)
    rows[0][2]["value"] = "금액"
    rows[0][3]["value"] = "수량"
    rows[0][4]["value"] = "단가"
    items, overview = record_summary_report(source)
    assert "전자제품 구매 내역" in overview
    assert "구매금액" in overview and "구매수량" in overview
    assert "판매금액" not in overview and "판매 내역" not in overview
    assert "2023년 11월 19일" in overview and "2024년 6월 12일" in overview
    assert _metric(items, "금액").topic == "금액"


def test_explicitly_linked_description_supplies_subject_sample_and_evidence():
    source = _records("Data")
    _notes(source, "Data: Sales order records from a fictional furniture company",
           "OtherData: Sales forecast records", "Insurance Policies Sample Data")
    items, overview = record_summary_report(source)
    assert "가구 판매 내역" in overview and "예시 자료" in overview
    assert "'Guide'!C2" in _metric(items).evidence
    assert "'Guide'!C3" not in _metric(items).evidence
    assert "'Guide'!C4" not in _metric(items).evidence
    assert "보험" not in overview and "예측" not in overview


def test_other_example_links_and_similar_sheet_names_cannot_supply_context():
    source = _records("Sales")
    _notes(source, "Food Sales Sample Data", "Insurance Policies Sample Data",
           "SalesArchive: Purchase forecast records from a fictional food company")
    items, overview = record_summary_report(source)
    assert "판매 내역" in overview
    assert "식품" not in overview and "예시 자료" not in overview
    assert not any(ref.startswith("'Guide'!") for ref in _metric(items).evidence)


@pytest.mark.parametrize("description", [
    "BookSales: Sales forecast records",
    "BookSales: Sales returns records",
    "BookSales: Planned sales records",
    "BookSales: Sales budget records",
    "BookSales: Not sales transactions",
])
def test_explicit_qualifier_vetoes_sales_title_without_blocking_valid_totals(description):
    source = _records()
    _notes(source, description)
    items, overview = record_summary_report(source)
    assert items and "금액" in overview and "100" in overview
    assert "판매 내역" not in overview and "판매금액" not in overview
    assert "도서" not in overview


@pytest.mark.parametrize("table_name", ["SalesForecast", "SalesReturns"])
def test_matching_table_qualifier_overrides_unqualified_sheet_title(table_name):
    source = _records()
    source["sheets"][0]["table_samples"] = [{"name": table_name, "reference": "A1:F7"}]
    items, overview = record_summary_report(source)
    assert items and "100" in overview
    assert "판매 내역" not in overview and "판매금액" not in overview


def test_sales_purchase_conflict_stays_neutral_and_keeps_the_numeric_answer():
    source = _records()
    _notes(source, "BookSales: Purchase transactions")
    items, overview = record_summary_report(source)
    assert _metric(items).topic == "TotalPrice"
    assert "100" in overview and "21" in overview
    assert "판매 내역" not in overview and "구매 내역" not in overview


def test_truncated_table_samples_do_not_make_a_multi_table_sheet_unambiguous():
    source = _records()
    sheet = source["sheets"][0]
    sheet["table_count"] = 2
    sheet["table_samples"] = [{"name": "Transactions", "reference": "A1:F7"}]
    _notes(source, "BookSales: Sales order records from a fictional book company")
    items, overview = record_summary_report(source)
    assert items and "100" in overview
    assert "도서" not in overview and "판매 내역" not in overview
    assert "예시 자료" not in overview
    assert "'Guide'!C2" not in _metric(items).evidence


def test_exact_named_table_can_supply_context_in_a_multi_table_sheet():
    source = _records("Data")
    sheet = source["sheets"][0]
    sheet["table_count"] = 2
    sheet["table_samples"] = [
        {"name": "BookSales", "reference": "$A$1:$F$7"},
        {"name": "InsurancePolicies", "reference": "H1:M7"},
    ]
    _notes(source, "BookSales: Sales order records from a fictional book company",
           "InsurancePolicies: Insurance policies sample data")
    items, overview = record_summary_report(source)
    assert "도서 판매 내역" in overview and "예시 자료" in overview
    assert "'Guide'!C2" in _metric(items).evidence
    assert "'Guide'!C3" not in _metric(items).evidence


def test_a_named_table_elsewhere_cannot_name_the_selected_record_region():
    source = _records("Data")
    sheet = source["sheets"][0]
    sheet["table_count"] = 2
    sheet["table_samples"] = [{"name": "BookSales", "reference": "H1:M7"}]
    _notes(source, "BookSales: Sales order records from a fictional book company")
    items, overview = record_summary_report(source)
    assert items and "100" in overview
    assert "도서" not in overview and "판매 내역" not in overview
    assert "예시 자료" not in overview


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


def test_generic_category_is_not_assumed_to_be_a_product_category():
    source = _records("Sales")
    for row, value in zip(_rows(source)[1:], ["Online"] * 3 + ["Retail"] * 3):
        row[1]["value"] = value
    _, overview = record_summary_report(source)
    assert "분류 항목" in overview and "Online" in overview and "Retail" in overview
    assert "제품 분류" not in overview


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
