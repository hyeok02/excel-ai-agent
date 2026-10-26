"""Do not fabricate concentration from mismatched populations or missing rows."""
import pytest

from tests.support.share_interpretation_fixtures import RANKED, context, interpretations


@pytest.mark.parametrize("complete", [False, None])
def test_incomplete_or_unknown_completeness_does_not_claim_interpretation(complete):
    assert interpretations(context(RANKED, complete=complete)) == []


@pytest.mark.parametrize("values", [
    [(1, "Alpha", 500, 50), (2, "Beta", 300, 10)],
    [(1, "Alpha", 500, 50), (2, "Alpha", 300, 30)],
    [(1, "Alpha", 500, 50), (2, "Beta", None, 30)],
    [(1, "Alpha", 500, 50), (2, "Beta", 300, None)],
    [(1, "Alpha", 500, 50), (2, "Beta", -300, 30)],
    [(1, "Alpha", 500, 50), (2, "Beta", 300, -30)],
])
def test_mismatched_denominators_duplicates_and_missing_values_are_rejected(values):
    assert interpretations(context(values)) == []


def test_same_numbers_in_different_periods_do_not_form_a_population():
    data = context([(1, "Alpha", 500, 50, "2024"), (2, "Beta", 300, 30, "2025")],
                   ("Rank", "Name", "Quantity", "Share (%)", "Period"))
    assert interpretations(data) == []


@pytest.mark.parametrize("values", [
    [(1, "Alpha", 500, 50), (3, "Beta", 300, 30)],
    [(1, "Alpha", 500, 50), (1, "Beta", 300, 30)],
    [(1, "Alpha", 300, 30), (2, "Beta", 500, 50)],
    [(1, "Alpha", 700, 70), (2, "Beta", 600, 60)],
    [(None, "Alpha", 500, 50), (2, "Beta", 300, 30)],
])
def test_gaps_duplicates_misordered_ranks_and_excess_totals_do_not_claim_top_n(values):
    items = interpretations(context(values))
    assert all("상위" not in item.title for item in items)


def test_escaped_percentage_format_does_not_scale_the_literal_value_twice():
    data = context([(1, "Alpha", 500, 50), (2, "Beta", 300, 30)])
    for row in data["sheets"][0]["business_facts"]["table_regions"][0]["rows"][1:]:
        row[-1]["number_format"] = "0.00\\%"
    assert any("80%" in item.fact for item in interpretations(data))


def test_unranked_overlapping_groups_are_never_summed():
    items = interpretations(context([("Group A", 600, 60), ("Group B", 500, 50)],
                                   ("Category", "Quantity", "Share (%)")))
    assert len(items) == 1 and "10%p" in items[0].fact
    assert "합계" not in items[0].fact


def test_quantity_units_cannot_be_borrowed_between_rows():
    data = context(RANKED)
    rows = data["sheets"][0]["business_facts"]["table_regions"][0]["rows"]
    rows[2][2]["number_format"] = '0 "kg"'
    assert interpretations(data) == []


def test_nonfinite_rank_never_raises_or_receives_a_concentration_claim():
    data = context([(float("nan"), "Alpha", 500, 50), (2, "Beta", 300, 30)])
    assert all("상위" not in item.title for item in interpretations(data))


def test_category_comparison_preserves_an_explicit_company_axis():
    data = context([("Group A", "Company A", 700, 70), ("Group B", "Company B", 400, 40)],
                   ("Category", "Company Name", "Quantity", "Share (%)"))
    assert interpretations(data) == []


@pytest.mark.parametrize("incomplete", [
    (1, "Other", "NA", "NA"), (4, "Other", None, None),
    (6, "Holder 1", "NA", "NA"), (None, "Holder 2", None, None),
    (None, "Unknown position", 100, 10),
    ("1", "Other", "NA", "NA"), ("4.0", "Other", "NA", "NA"),
])
def test_incomplete_duplicate_upper_rank_or_identity_cannot_hide_behind_value_filter(incomplete):
    data = context([(rank, f"Holder {rank}", 600 - rank * 100, 6 - rank)
                    for rank in range(1, 6)] + [incomplete])
    assert all("상위" not in item.title for item in interpretations(data))


def test_lower_missing_values_remain_in_the_identity_evidence():
    data = context([(1, "Alpha", 500, 50), (2, "Beta", 300, 30), (3, "Other", "NA", "NA")])
    item = next(item for item in interpretations(data) if "상위 2개" in item.title)
    assert {"'Data'!A4", "'Data'!B4"} <= set(item.evidence)
