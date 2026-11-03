"""A business record subject needs a positive, source-scoped definition."""
import pytest

from app.services.insights.models import WorkbookInsightReport, InsightValidationStatus
from app.services.insights.narratives.record_summary import record_summary_report
from app.services.insights.verification.validator import _validate_insight, validate_workbook_insights
from app.services.insights.verification.validation_index import workbook_evidence_index
from tests.test_record_context_grounding import _notes
from tests.test_record_summary_readability import _cell, _rows, _source


def _records(description="Ledger sheet has commercial property policy data for a fictional insurance company"):
    source = _source(amount="InsuredValue", quantity="RecordCount", category="State",
                     labels=["NY"] * 3 + ["CA"] * 3)
    source["sheets"][0]["name"] = "Ledger"
    rows = _rows(source)
    rows[0][0]["value"] = "Policy"
    rows[0][-1]["value"] = "Location"
    rows[0].append(_cell("F1", "Expiry"))
    for i, row in enumerate(rows[1:], 2):
        row[-1]["value"] = "Urban"
        row.append(_cell(f"F{i}", f"2024-03-{i:02d}", "yyyy-mm-dd"))
    if description:
        _notes(source, description)
    return source


def _amount(items):
    return next(item for item in items if item.topic == "InsuredValue" and item.category == "metric")


def test_explicit_property_policy_definition_provides_subject_and_preserves_expiry_role():
    source = _records()
    items, overview = record_summary_report(source)
    assert "상업용 부동산 보험 계약 6건" in overview
    assert "예시 자료" in overview and "보험가액 합계는 100" in overview
    assert "지역(State)별" in overview and "‘NY’" in overview
    assert "2024년" not in overview and "판매" not in overview
    assert "'Guide'!C2" in _amount(items).evidence
    assert "'Ledger'!F2:F7" not in _amount(items).evidence


@pytest.mark.parametrize("definition, expected", [
    ("Ledger: vehicle insurance policy records", "차량 보험 계약"),
    ("Ledger sheet contains residential property policy records", "주거용 부동산 보험 계약"),
    ("Ledger: insurance policy data", "보험 계약"),
    ("Ledger: employee attendance records", "직원 근태 기록"),
    ("Ledger: inventory data", "재고 기록"),
    ("Ledger: customer invoice records", "고객 청구서 기록"),
])
def test_declarations_are_generic_across_record_types(definition, expected):
    _, overview = record_summary_report(_records(definition))
    assert expected in overview
    assert "보험가액 합계는 100" in overview


def test_unknown_modifier_is_preserved_instead_of_partially_translated_away():
    _, overview = record_summary_report(_records("Ledger: lunar vehicle policy data"))
    assert "‘lunar vehicle policy’ 기록" in overview
    assert "차량 보험 계약" not in overview


def test_policy_word_alone_without_insurance_schema_does_not_become_insurance():
    source = _records("Ledger: commercial policy data")
    _rows(source)[0][2]["value"] = "TotalAmount"
    _, overview = record_summary_report(source)
    assert "‘commercial policy’ 기록" in overview
    assert "보험 계약" not in overview


@pytest.mark.parametrize("description", [
    "OtherLedger: commercial property policy data",
    "Insurance Policies Sample Data",
    "Ledger: not commercial property policy data",
    "Ledger: commercial property policy data excluding cancelled policies",
])
def test_unscoped_or_qualified_definitions_do_not_assert_unqualified_subject(description):
    items, overview = record_summary_report(_records(description))
    assert items and "100" in overview
    assert "보험 계약" not in overview


def test_conflicting_record_definitions_preserve_totals_but_do_not_pick_a_subject():
    source = _records()
    source["sheets"][1]["business_facts"]["table_regions"][0]["rows"].append(
        [_cell("C3", "Ledger: employee attendance records")]
    )
    items, overview = record_summary_report(source)
    assert items and "보험가액 합계는 100" in overview
    assert "보험 계약" not in overview and "직원 근태" not in overview


def test_state_is_not_translated_geographically_without_a_geographic_schema():
    source = _records()
    _rows(source)[0][4]["value"] = "Counter"
    _, overview = record_summary_report(source)
    assert "State별" in overview
    assert "지역(State)" not in overview


def test_geographic_grouping_requires_its_schema_evidence_even_without_definition():
    source = _records(None)
    items, overview = record_summary_report(source)
    item = next(item for item in items if item.category == "summary")
    assert "지역(State)" in overview
    assert "'Ledger'!E1" in item.evidence
    changed = item.model_copy(update={"evidence": [ref for ref in item.evidence if ref != "'Ledger'!E1"]})
    assert _validate_insight(changed, workbook_evidence_index(source), items) is None


def test_generic_date_header_on_policies_is_not_inferred_as_transaction_period():
    source = _records()
    _rows(source)[0][-1]["value"] = "Date"
    _, overview = record_summary_report(source)
    assert "보험 계약" in overview
    assert "2024년" not in overview


def test_definition_context_survives_canonical_validation():
    source = _records()
    report = validate_workbook_insights(WorkbookInsightReport(overview="", insights=[]), source)
    assert report.insights
    assert all(item.validation_status == InsightValidationStatus.VERIFIED for item in report.insights)
    assert "상업용 부동산 보험 계약" in report.overview
    assert report.validation.overview_validated


@pytest.mark.parametrize("tamper", ["subject", "definition_ref"])
def test_wrong_subject_or_missing_definition_cannot_inherit_verification(tamper):
    source = _records()
    items, _ = record_summary_report(source)
    item = _amount(items)
    if tamper == "subject":
        item = item.model_copy(update={"fact": item.fact.replace("상업용 부동산", "차량")})
    else:
        item = item.model_copy(update={"evidence": [ref for ref in item.evidence if ref != "'Guide'!C2"]})
    assert _validate_insight(item, workbook_evidence_index(source), items) is None
