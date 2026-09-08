from app.services.insights.facts.fact_trends import numeric_changes
from app.services.insights.narratives.horizontal_trends import horizontal_trend_report
from app.services.insights.quality import build_source_report
from app.services.insights.narratives.source_narratives import source_narrative_report


def _series(metric="Total Revenue", values=(6.026, 4.725), fmt="0.0\\%"):
    return {
        "metric": metric,
        "label_cell": "B100",
        "scope": "1 Year Growth (%)",
        "scope_cell": "B99",
        "basis": None,
        "points": [
            {
                "period": period,
                "period_cell": f"{column}98",
                "value": value,
                "value_cell": f"{column}100",
                "number_format": fmt,
            }
            for period, column, value in zip(
                ("2024-01-31T00:00:00", "2026-01-31T00:00:00"),
                "DF",
                values,
            )
        ],
    }


def test_horizontal_percentage_is_a_grounded_info_trend():
    context = {"sheets": [{"name": "CompanySummary", "business_facts": {
        "horizontal_series": [_series()],
    }}]}

    items, overview = horizontal_trend_report(context)

    assert len(items) == 1
    assert items[0].category == "trend"
    assert items[0].severity == "info"
    assert "6.03%" in overview and "4.72%" in overview
    assert "159" not in overview
    assert items[0].evidence == [
        "'CompanySummary'!B99", "'CompanySummary'!B100",
        "'CompanySummary'!D98", "'CompanySummary'!D100",
        "'CompanySummary'!F98", "'CompanySummary'!F100",
    ]


def test_internal_identifier_trend_cannot_override_visible_metric():
    internal = {
        "name": "Intermediate",
        "business_facts": {"numeric_changes": [{
            "metric": "SP_VOLUME", "earliest_period": "2025-01-01",
            "latest_period": "2025-02-01", "earliest_value": 1,
            "latest_value": 2, "change": 1, "change_rate_percent": 100,
            "evidence": ["Intermediate!A1:B2"],
        }]},
    }
    visible = {"name": "CompanySummary", "business_facts": {
        "horizontal_series": [_series("Revenue", (100, 120), "General")],
    }}

    report = source_narrative_report({"sheets": [internal, visible]})

    assert report.insights and "Revenue" in report.overview
    assert "SP_VOLUME" not in report.model_dump_json()


def test_identifier_columns_never_become_numeric_trends():
    records = [
        {"values": [
            {"value": "2025-01-01"}, {"label": "OID", "value": 39182139},
            {"label": "Headcount", "value": 100},
        ], "location": "Data!A1:C1"},
        {"values": [
            {"value": "2025-02-01"}, {"label": "OID", "value": 39281873},
            {"label": "Headcount", "value": 120},
        ], "location": "Data!A2:C2"},
    ]

    changes = numeric_changes(records)

    assert [change["metric"] for change in changes] == ["Headcount"]


def test_event_and_transaction_fallback_hide_provider_identifiers():
    context = {"sheets": [{"name": "Transactions", "business_facts": {
        "numeric_changes": [],
        "selected_records": [{"values": [
            {"cell": "A2", "label": "Company Name", "value": "Alpha Inc."},
            {"cell": "B2", "label": "MI Transaction ID", "value": "SPTRD123"},
            {"cell": "C2", "label": "Announced Date", "value": "2025-01-03"},
            {"cell": "D2", "label": "Percent Owned (%)", "value": 90},
        ]}],
    }}]}

    report = build_source_report(context)

    assert report.insights[0].category == "metric"
    assert "Alpha Inc." in report.overview and "90%" in report.overview
    assert "SPTRD" not in report.model_dump_json()
