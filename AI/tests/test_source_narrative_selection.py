"""The workbook's focal sheets must win over ancillary comparison patterns."""
from app.services.insights.source_narratives import source_narrative_report


def _cell(address, value):
    return {"cell": address, "value": value, "number_format": "General"}


def _ranked_sheet():
    rows = [
        [_cell("A1", "Rank"), _cell("B1", "Name"),
         _cell("C1", "Shares Held"), _cell("D1", "Share (%)")],
        [_cell("A2", 1), _cell("B2", "Primary Fund"),
         _cell("C2", 1_000), _cell("D2", 42)],
    ]
    return {"name": "Ownership", "business_facts": {
        "table_regions": [{"rows": rows}],
    }}


def _peer_trend_sheet():
    change = {
        "metric": "Peer revenue", "earliest_period": "2024-01-01",
        "latest_period": "2025-01-01", "earliest_value": 100,
        "latest_value": 200, "change": 100, "change_rate_percent": 100,
        "evidence": ["Peer_Comparison!A2:B3"],
    }
    return {"name": "Peer_Comparison", "business_facts": {
        "numeric_changes": [change], "selected_records": [],
    }}


def test_focal_ranked_table_precedes_comparison_sheet_trend():
    context = {"sheets": [_peer_trend_sheet(), _ranked_sheet()]}

    report = source_narrative_report(context)

    assert report.insights and "Primary Fund" in report.insights[0].fact
    assert "Peer revenue" not in report.overview
