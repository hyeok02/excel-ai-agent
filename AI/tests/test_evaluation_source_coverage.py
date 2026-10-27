"""Source coverage must neither pass invalid ranges nor walk every source cell."""
import pytest

from evals.run_questions import evidence_errors


@pytest.mark.parametrize("target", ["Right!B3:A1", "Right!A0", "Right!A:A", "Right!XFE1",
                                     "Right!A1048577", "Right!A1:B0", "A1", "!A1", None])
def test_invalid_oracle_range_cannot_pass_by_vacuous_coverage(target):
    assert any("Invalid source coverage target" in error for error in evidence_errors([target], []))


def test_excel_quoted_sheet_names_absolute_and_lowercase_coordinates_are_normalized():
    evidence = [{"sheet_name": "Owner's data", "reference": "$b$2:$c$3"}]
    assert evidence_errors(["'Owner''s data'!$B$2:C3"], evidence) == []
    assert evidence_errors(["'Other data'!B2:C3"], evidence)


def test_union_coverage_checks_the_inside_not_only_corners_or_outer_bounds():
    evidence = [{"sheet_name": "Right", "reference": reference}
                for reference in ("A1:C1", "A3:C3", "A2", "C2")]
    assert evidence_errors(["Right!A1:C3"], evidence)
    assert evidence_errors(["Right!A1:C3"], [*evidence, {"sheet_name": "Right", "reference": "B2"}]) == []


def test_adjacent_rectangles_cover_a_large_target_without_cell_enumeration():
    evidence = [{"sheet_name": "Right", "reference": "A1:LZZ1048576"},
                {"sheet_name": "Right", "reference": "MAA1:XFD1048576"}]
    assert evidence_errors(["Right!A1:XFD1048576"], evidence) == []


def test_invalid_returned_evidence_cannot_supply_the_missing_cell():
    evidence = [None, "Right!B2", {"sheet_name": "Right", "reference": "B3:A1"},
                {"sheet_name": "Wrong", "reference": "A1:C3"}]
    assert evidence_errors(["Right!B2"], evidence)
