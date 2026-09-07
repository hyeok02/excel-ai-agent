from copy import deepcopy

import pytest

from app.services.insights.business_facts import build_business_facts
from app.services.insights.comparable_transactions import extract_comparable_transactions
from app.services.insights.models import WorkbookInsightReport
from app.services.insights.source_narratives import source_narrative_report
from app.services.insights.source_records import source_record_insights
from app.services.insights.validator import validate_workbook_insights


def _cell(address, value):
    return {"address": address, "value": value, "number_format": "General"}


def _column(*cells):
    return {"analysis_rows": [[_cell(address, value)] for address, value in cells]}


def _regions():
    peer_rows = range(12, 22)
    values = [832.495281, 713.844531, 1795.885, 1794.314525, 3607.868628,
              4888.691378, 833.783492, 665.00652, 1559.485587, 422.7273]
    multiples = ["NA", "NA", 2.31, "NA", "NA", 16.88, "NA", "NA", 9.99, "NA"]
    return [
        _column(("A1", "Comparable M&A Transactions"),
                ("A2", "Focus Transaction ID"), ("A10", "Transaction IDs"),
                *((f"A{row}", f"PX{row}") for row in peer_rows), ("A28", "FX1")),
        _column(("B2", "FX1"), ("B10", "Target/Issuer Name"),
                *((f"B{row}", f"Peer {row}") for row in peer_rows),
                ("B28", "Focus Company")),
        _column(("C10", "Total Transaction Value ($M)"),
                *((f"C{row}", value) for row, value in zip(peer_rows, values)),
                ("C28", 911.841102)),
        _column(("D10", "Deal Value/ EBITDA (x)"),
                *((f"D{row}", value) for row, value in zip(peer_rows, multiples)),
                ("D28", 5.09)),
        _column(("E10", "Transaction Value/ EBITDA (x)"),
                *((f"E{row}", value) for row, value in zip(peer_rows, multiples)),
                ("E23", 16.88), ("E24", 9.99), ("E25", 2.31),
                ("E26", 9.73), ("E28", 5.09)),
        _column(("F23", "High"), ("F24", "Median"),
                ("F25", "Low"), ("F26", "Average")),
    ]


def test_fragmented_comparable_table_extracts_focus_medians_and_coverage():
    result = extract_comparable_transactions("Deal Review", _regions())

    assert result["subject"] == "Focus Company"
    assert result["peer_count"] == 10
    multiple, value = result["metrics"]
    assert multiple["header_cell"] == "E10"
    assert (multiple["subject_value"], multiple["median"]) == (5.09, 9.99)
    assert multiple["valid_count"] == 3
    assert multiple["median_cell"] == "E24"
    assert value["median"] == pytest.approx(1196.6345395)


def test_comparable_narrative_is_selected_before_row_dump_fallbacks():
    facts = build_business_facts("Deal Review", _regions(), [], 4)
    context = {"sheets": [{"name": "Deal Review", "business_facts": facts}]}

    report = source_narrative_report(context)

    assert [item.category for item in report.insights] == ["metric", "metric"]
    facts = " ".join(item.fact for item in report.insights)
    assert "5.09배" in facts and "9.99배" in facts
    assert "10건 중 3건" in report.overview
    assert "23.8%" in report.overview and "49.0%" in report.overview
    assert "$911.8M" in facts and "$1,196.6M" in facts
    assert "'Deal Review'!E12:E21" in report.insights[0].evidence


def test_multiple_with_fewer_than_three_values_is_not_reported():
    regions = deepcopy(_regions())
    target = next(row[0] for row in regions[4]["analysis_rows"]
                  if row[0]["address"] == "E14")
    target["value"] = "NA"

    result = extract_comparable_transactions("Deal Review", regions)

    assert [metric["kind"] for metric in result["metrics"]] == ["transaction_value"]


def test_declared_focus_id_must_match_the_subject_row():
    regions = deepcopy(_regions())
    regions[0]["analysis_rows"][-1][0]["value"] = "OTHER"

    assert extract_comparable_transactions("Deal Review", regions) is None


def test_zero_median_is_not_turned_into_a_percentage():
    regions = deepcopy(_regions())
    for address in ("E14", "E17", "E20", "E23", "E24", "E25", "E26"):
        target = next(row[0] for row in regions[4]["analysis_rows"]
                      if row[0]["address"] == address)
        target["value"] = 0

    result = extract_comparable_transactions("Deal Review", regions)

    assert [metric["kind"] for metric in result["metrics"]] == ["transaction_value"]


def test_validated_comparison_does_not_append_transaction_row_dumps():
    facts = build_business_facts("DealReview", _regions(), [], 4)
    facts["selected_records"].append({
        "location": "DealReview!G40:H40",
        "values": [
            {"cell": "G40", "label": "Company Name", "value": "Noise Corp",
             "number_format": "General", "label_cell": "G39"},
            {"cell": "H40", "label": "Percent Owned (%)", "value": 100,
             "number_format": "General", "label_cell": "H39"},
        ],
    })
    context = {"sheets": [{"name": "DealReview", "business_facts": facts}]}
    row_dump = source_record_insights(context, 1)

    report = validate_workbook_insights(
        WorkbookInsightReport(overview="raw", insights=row_dump), context
    )

    assert len(row_dump) == 1
    assert len(report.insights) == 2
    assert all("Noise Corp" not in item.fact for item in report.insights)
