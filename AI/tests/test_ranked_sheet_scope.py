import pytest

from app.services.insights.ranked_narratives import ranked_report


def _cell(address, value):
    return {"cell": address, "value": value, "number_format": "General"}


def _ranked_sheet(name, holder, percent):
    rows = [
        [_cell("A1", "Rank"), _cell("B1", "Name"),
         _cell("C1", "Shares Held"), _cell("D1", "Share (%)")],
        [_cell("A2", 1), _cell("B2", holder),
         _cell("C2", 1_000), _cell("D2", percent)],
    ]
    return {"name": name, "business_facts": {
        "table_regions": [{"title": "Top Holders", "rows": rows}],
    }}


def test_mixed_summary_sheet_is_not_excluded_by_one_region_title():
    summary = _ranked_sheet("Summary", "Primary Fund", 42)
    summary["content_outline"] = {"region_titles": ["Top Holders", "Peer Comparison"]}
    context = {"sheets": [summary, _ranked_sheet("Notes", "Secondary Fund", 60)]}

    insights, _ = ranked_report(context)

    assert insights and "Primary Fund" in insights[0].fact


@pytest.mark.parametrize("name", ["Peers", "PeerGroup", "Competitors"])
def test_common_comparison_sheet_names_are_excluded(name):
    context = {"sheets": [
        _ranked_sheet(name, "Peer Fund", 95),
        _ranked_sheet("Ownership", "Primary Fund", 42),
    ]}

    insights, _ = ranked_report(context)

    assert insights and all("Peer Fund" not in item.fact for item in insights)
