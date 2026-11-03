"""Record summaries require complete values and correct source selection."""
from app.services.insights.facts.series_scalars import unit
from app.services.insights.narratives.record_summary import record_summary_report
from app.services.insights.narratives.source_narratives import source_narrative_report
from tests.support.recent_record_fixtures import cell, context, record_rows


def test_record_totals_and_group_concentration_exclude_unit_price():
    items, overview = record_summary_report(context(record_rows()))
    assert len(items) == 2
    assert "기록 5건" in overview and "40" in items[0].fact
    assert "North" in items[1].fact and "75%" in items[1].fact
    assert "UnitPrice" not in overview
    assert "'Data'!C2:C6" in items[0].evidence


def test_record_totals_require_unique_keys_and_complete_values():
    rows = record_rows()
    rows[-1][0]["value"] = rows[-2][0]["value"]
    assert not record_summary_report(context(rows))[0]
    rows = record_rows()
    rows[-1][2]["value"] = None
    assert not record_summary_report(context(rows))[0]
    assert not record_summary_report(context(record_rows(), complete=False))[0]


def test_record_totals_never_add_subtotals_or_percentages():
    rows = record_rows()
    rows[-1][1]["value"] = "Grand Total"
    assert not record_summary_report(context(rows))[0]


def test_record_totals_reject_mixed_currency_and_prefixed_subtotal():
    rows = record_rows()
    rows[0].append(cell("E1", "Currency"))
    for i, row in enumerate(rows[1:], 2):
        row.append(cell(f"E{i}", "USD" if i % 2 else "EUR"))
    assert not record_summary_report(context(rows))[0]
    rows = record_rows()
    rows[-1][1]["value"] = "North Total"
    assert not record_summary_report(context(rows))[0]
    rows = record_rows()
    for row in rows[1:]:
        row[2]["number_format"] = "0.0%"
    assert not record_summary_report(context(rows))[0]


def test_record_header_can_be_adjacent_separate_region_only():
    rows = record_rows()
    ctx = context([])
    regions = ctx["sheets"][0]["business_facts"]["table_regions"]
    regions[:] = [{"rows": rows[:1]}, {"rows": rows[1:]}]
    assert record_summary_report(ctx)[0]
    for c in rows[0]:
        c["cell"] = c["cell"].replace("1", "9")
    assert not record_summary_report(ctx)[0]


def test_accounting_placeholder_is_not_a_unit():
    assert unit(cell("A1", 3, '_-* #,##0_-;\\-* #,##0_-;_-* "-"??_-;_-@_-')) == ""
    assert unit(cell("A1", 3, '0 "kg";-0 "kg";0 "kg"')) == "kg"


def test_source_selection_prefers_keyed_records_to_front_sheet_ranges():
    raw = [[cell("A1", "Category"), cell("B1", "Value")]] + [
        [cell(f"A{i}", f"C{i}"), cell(f"B{i}", i)] for i in range(2, 7)]
    ctx = context(raw, "Summary")
    ctx["sheets"].extend(context(record_rows(), "Transactions")["sheets"])
    result = source_narrative_report(ctx)
    assert result.insights[0].title == "금액 합계"
    assert result.insights[0].topic == "TotalAmount"
    assert "값 범위" not in result.overview
