from app.agent.query.references import (
    extract_references,
    matching_references,
    normalize_reference,
)


def test_normalizes_quoted_and_unquoted_space_sheet_names() -> None:
    expected = "sales data!a1"

    assert normalize_reference("Sales Data!$A$1") == expected
    assert normalize_reference("'Sales Data'!$A$1") == expected
    assert extract_references("Source: 'Sales Data'!$A$1") == [expected]


def test_space_sheet_names_do_not_collide() -> None:
    sales = normalize_reference("Sales Data!A1")
    costs = normalize_reference("Cost Data!A1")

    assert sales == "sales data!a1"
    assert costs == "cost data!a1"
    assert sales != costs


def test_matches_range_on_space_and_apostrophe_sheet_name() -> None:
    citation = normalize_reference("'Owner''s Data'!A1:B2")
    available = {
        normalize_reference("Owner's Data!A1"),
        normalize_reference("Owner's Data!B2"),
        normalize_reference("Other Data!A1"),
    }

    assert citation is not None
    assert None not in available
    assert matching_references(citation, available) == {
        "owner's data!a1",
        "owner's data!b2",
    }


def test_rejects_text_wrapped_around_reference() -> None:
    assert normalize_reference("see Sales Data!A1 for details") is None
