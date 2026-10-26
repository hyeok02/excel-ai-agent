"""Source-grounded interpretation goes beyond repeating individual cell values."""
from io import BytesIO

from openpyxl import Workbook

from app.services.insights.facts.context import build_workbook_context
from app.services.insights.quality import build_source_report
from app.services.insights.verification.validator import validate_workbook_insights
from app.services.workbook_parser import parse_workbook
from tests.support.share_interpretation_fixtures import RANKED, context, interpretations


def test_ranked_table_explains_top_concentration_and_gap_instead_of_only_values():
    items = interpretations(context(RANKED))
    concentration = next(item for item in items if "상위 3개" in item.title)
    gap = next(item for item in items if "비중 차이" in item.title)
    assert "90%" in concentration.fact
    assert "Alpha 50%" in concentration.fact and "Beta 30%" in concentration.fact
    assert "20%p 더 높습니다" in gap.fact
    assert {"'Data'!A2", "'Data'!A3", "'Data'!A4", "'Data'!C3", "'Data'!D3"} <= set(concentration.evidence)


def test_category_totals_are_compared_without_adding_overlapping_classifications():
    data = context([("Group A", 700, 70), ("Group B", 400, 40)],
                   ("Category", "Quantity", "Share (%)"))
    items = interpretations(data)
    assert len(items) == 1 and "30%p 더 높습니다" in items[0].fact
    assert "110%" not in items[0].fact and "합계" not in items[0].fact


def test_top_n_is_bounded_and_cites_all_rows_used_to_check_the_ranking():
    data = context([(rank, f"Holder {rank}", 70 - rank * 10, 7 - rank)
                    for rank in range(1, 7)])
    concentration = next(item for item in interpretations(data) if "상위 5개" in item.title)
    assert "20%" in concentration.fact
    assert "Holder 6" not in concentration.fact
    assert "'Data'!A7" in concentration.evidence and "'Data'!B7" in concentration.evidence
    assert "'Data'!D7" not in concentration.evidence


def test_real_parser_and_validator_keep_computed_interpretation_verified():
    workbook = Workbook()
    workbook.active.title = "Arbitrary holdings"
    workbook.active.append(["Rank", "Name", "Quantity", "Share (%)"])
    for row in RANKED:
        workbook.active.append(row)
    stream = BytesIO()
    workbook.save(stream)
    workbook.close()
    data = build_workbook_context(parse_workbook("generic.xlsx", stream.getvalue()))
    report = validate_workbook_insights(build_source_report(data), data)
    item = next(item for item in report.insights if "상위 3개" in item.title)
    assert "90%" in item.fact and item.validation_status == "verified"


def test_fractional_percent_format_has_the_same_meaning_as_percent_values():
    data = context([(1, "Alpha", 500, 0.5), (2, "Beta", 300, 0.3)])
    for row in data["sheets"][0]["business_facts"]["table_regions"][0]["rows"][1:]:
        row[-1]["number_format"] = "0.00%"
    items = interpretations(data)
    assert any("80%" in item.fact for item in items)
    assert any("20%p" in item.fact for item in items)


def test_available_category_values_can_be_compared_without_filling_missing_categories():
    data = context([("Group A", 700, 70), ("Group B", 400, 40), ("Group C", "NA", "NA")],
                   ("Category", "Quantity", "Share (%)"))
    items = interpretations(data)
    assert len(items) == 1 and "30%p" in items[0].fact
    assert "Group C" not in items[0].fact


def test_rounding_intervals_reconcile_percentages_with_a_shared_quantity_base():
    data = context([(1, "Alpha", 139021, 27.8), (2, "Beta", 72993, 14.6),
                    (3, "Gamma", 60009, 12.0)])
    assert any("54.4%" in item.fact for item in interpretations(data))


def test_missing_lower_rank_values_do_not_hide_the_complete_top_five():
    data = context([(i, f"Holder {i}", (7 - i) * 100, (7 - i) * 10) for i in range(1, 6)]
                   + [(6, "Other", "NA", "NA")])
    # The first five deliberately exceed 100%; use a common 10,000-unit base.
    for row in data["sheets"][0]["business_facts"]["table_regions"][0]["rows"][1:6]:
        row[-1]["value"] /= 10
    assert any("상위 5개" in item.title and "20%" in item.fact for item in interpretations(data))


def test_earlier_aggregate_sheet_cannot_crowd_out_later_ranked_concentration():
    groups = context([("All Groups", 900, 90), ("Group A", 700, 70), ("Group B", 400, 40)],
                     ("Category", "Quantity", "Share (%)"))["sheets"]
    groups[0]["name"] = "Composition"
    ranked = context(RANKED)["sheets"]
    ranked[0]["name"] = "Ranked details"
    items = interpretations({"sheets": [*groups, *ranked]})
    assert any("상위 3개" in item.title and "90%" in item.fact for item in items)
    assert any("비중 차이" in item.title for item in items)
