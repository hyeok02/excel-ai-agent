"""Readable wording cannot bypass evidence or complete-record requirements."""
import pytest

from app.services.insights.models import InsightValidationStatus, WorkbookInsightReport
from app.services.insights.narratives.record_summary import record_summary_report
from app.services.insights.verification.validation_index import workbook_evidence_index
from app.services.insights.verification.validator import _validate_insight, validate_workbook_insights
from tests.support.record_summary_fixtures import _cell, _rows, _source


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
