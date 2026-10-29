from random import Random

import pytest
from openpyxl.utils.cell import get_column_letter

from app.services.insights.verification import reference_matching as matching


def _legacy_matches(citation: str, available: set[str]) -> set[str]:
    cited_box = matching._box(citation)
    if cited_box is None or cited_box.area > matching.MAX_CITATION_AREA:
        return set()
    return {
        reference for reference in available
        if (candidate := matching._box(reference)) is not None
        and matching._contains(cited_box, candidate)
    }


@pytest.mark.parametrize("citation, expected", [
    ("Source!A1:B3", {"source!A1", "SOURCE!B3", "Source!B3:A2"}),
    ("sOuRcE!b3:a1", {"source!A1", "SOURCE!B3", "Source!B3:A2"}),
    ("Source!A1", {"source!A1"}),
    ("Other!A1:B3", {"Other!A1"}),
    ("Absent!A1:B3", set()),
    ("Source!A0:A1", {"Source!A0", "source!A1"}),
    ("Source!$A$1", set()),
    ("Source!AAAA1", set()),
    ("Source!A1 trailing text", set()),
    ("not a reference", set()),
])
def test_index_preserves_case_ranges_and_containment(citation, expected) -> None:
    available = {
        "source!A1", "SOURCE!B3", "Source!B3:A2", "Other!A1",
        "Source!A0", "Source!A1:C4", "Source!C1", "Source!B4", "invalid",
    }
    index = matching.ReferenceIndex.from_references(available)

    assert matching.matching_references(citation, index) == expected
    assert matching.matching_references(citation, available) == expected
    assert matching.matching_references(citation, index) == _legacy_matches(citation, available)


def test_index_keeps_area_limit_and_does_not_borrow_enclosing_range() -> None:
    available = {"Data!A1:CV100", "Data!B2", "Data!CV100", "Data!CW100"}
    index = matching.ReferenceIndex.from_references(available)

    assert matching.matching_references("Data!A1", index) == set()
    assert matching.matching_references("Data!A1:CV100", index) == {
        "Data!A1:CV100", "Data!B2", "Data!CV100",
    }
    assert matching.matching_references("Data!A1:CW100", index) == set()
    assert matching.matching_references("Data!CV100:A1", index) == {
        "Data!A1:CV100", "Data!B2", "Data!CV100",
    }


def test_index_preserves_sheet_spelling_and_does_not_add_normalization() -> None:
    available = {
        "Owner's Data!A1", "OWNER'S DATA!B2", "'Owner''s Data'!A1",
        "Owner's Data !A1", "Owner's Other Data!A1", "Owner's Data!C3\n",
    }
    index = matching.ReferenceIndex.from_references(available)
    for citation in ("Owner's Data!A1:C3", "'Owner''s Data'!A1", "Owner's Data !A1"):
        assert matching.matching_references(citation, index) == _legacy_matches(citation, available)


def test_index_matches_previous_algorithm_for_mixed_random_boxes() -> None:
    random = Random(103)

    def reference() -> str:
        sheet = random.choice(("SHEET ONE", "sheet one", "Sheet Two", "세 번째"))
        columns = [get_column_letter(random.randint(1, 60)) for _ in range(2)]
        rows = [random.randint(0, 600) for _ in range(2)]
        return f"{sheet}!{columns[0]}{rows[0]}:{columns[1]}{rows[1]}"

    available = {reference() for _ in range(500)} | {"invalid", "Sheet One!$A$1"}
    index = matching.ReferenceIndex.from_references(available)
    for citation in [reference() for _ in range(100)] + list(available)[:20]:
        assert matching.matching_references(citation, index) == _legacy_matches(citation, available)


def test_index_is_an_isolated_snapshot_and_results_are_not_shared() -> None:
    available = {"Data!A1"}
    original = matching.ReferenceIndex.from_references(available)
    available.clear()
    available.add("Data!B2")
    later = matching.ReferenceIndex.from_references(available)

    result = matching.matching_references("Data!A1:B2", original)
    result.add("Data!B2")
    assert matching.matching_references("Data!A1:B2", original) == {"Data!A1"}
    assert matching.matching_references("Data!A1:B2", later) == {"Data!B2"}


def test_resolve_parses_available_once_and_filters_unrelated_rows(monkeypatch) -> None:
    available = {f"Data!A{row}" for row in range(1, 15_001)}
    available.update(f"Other!A{row}" for row in range(1, 15_001))
    citations = {f"data!A{row}" for row in range(1, 121)}
    parse_count = 0
    containment_count = 0
    parse = matching._box
    contains = matching._contains

    def counted_parse(reference):
        nonlocal parse_count
        parse_count += 1
        return parse(reference)

    def counted_contains(outer, inner):
        nonlocal containment_count
        containment_count += 1
        return contains(outer, inner)

    monkeypatch.setattr(matching, "_box", counted_parse)
    monkeypatch.setattr(matching, "_contains", counted_contains)

    resolved, unmatched = matching.resolve_references(citations, available)

    assert resolved == {f"Data!A{row}" for row in range(1, 121)}
    assert unmatched == set()
    assert parse_count == len(available) + len(citations)
    assert containment_count == len(citations)


def test_prepared_index_is_reused_across_multiple_resolutions(monkeypatch) -> None:
    index = matching.ReferenceIndex.from_references({"Data!A1", "Other!A1"})
    parse = matching._box
    parsed = []

    def counted_parse(reference):
        parsed.append(reference)
        return parse(reference)

    monkeypatch.setattr(matching, "_box", counted_parse)
    for _ in range(10):
        assert matching.resolve_references({"Data!A1", "missing"}, index) == (
            {"Data!A1"}, {"missing"},
        )
    assert len(parsed) == 20
    assert "Other!A1" not in parsed
