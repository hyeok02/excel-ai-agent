from app.services.insights.facts.business_facts import build_business_facts


def _cell(address, value):
    return {
        "address": address, "value": value, "formula": None,
        "cached_value": None, "number_format": "General",
    }


def _region(*rows):
    return {
        "title": None, "semantic": {"role": "data"},
        "preview_rows": list(rows), "analysis_rows": list(rows),
    }


def test_row_oriented_trends_never_cross_region_boundaries():
    first = _region(
        [_cell("A1", "Date"), _cell("B1", "Total")],
        [_cell("A2", "2026-09-01"), _cell("B2", 100)],
    )
    second = _region(
        [_cell("D1", "Date"), _cell("E1", "Total")],
        [_cell("D2", "2026-09-02"), _cell("E2", 200)],
    )

    facts = build_business_facts("Sheet1", [first, second], [], 12)

    assert facts["numeric_changes"] == []
