"""Numeric measures and footer prose must never become verified check marks."""
import pytest

from app.services.insights.facts.flag_columns import flag_matrix, mark_of
from app.services.insights.models import WorkbookInsight, WorkbookInsightReport
from app.services.insights.narratives.flag_narratives import flag_matrix_report
from app.services.insights.verification.validation_index import workbook_evidence_index
from app.services.insights.verification.validator import _validate_insight, validate_workbook_insights


def _cell(address, value, fmt="General"):
    return {"cell": address, "value": value, "number_format": fmt}


def _context(rows):
    return {"sheets": [{"name": "Observations", "business_facts": {
        "table_regions": [{"rows": rows, "rows_complete": True}],
    }}]}


def _percentage_rows():
    rows = [[_cell("A1", "Year"), _cell("B1", "Good"), _cell("C1", "Moderate")]]
    rows += [[_cell(f"A{r}", 2017 + r), _cell(f"B{r}", .31 + r / 100, "0.0%"),
              _cell(f"C{r}", .69 - r / 100, "0.0%")]
             for r in range(2, 8)]
    rows += [[_cell("A8", "Source: annual survey")], [_cell("A9", "Note: percentages")]]
    return rows


@pytest.mark.parametrize("value", [.34, 0, -4, 0.0, True, "0.34", "0.0%", "-4", "ordinary", "volume", "xylophone"])
def test_numeric_measures_and_words_are_not_status_marks(value):
    assert mark_of(value) is None


@pytest.mark.parametrize("value,expected", [("O", "o"), ("×", "x"), ("✓", "v"),
    ("△(inspection pending)", "△"), ("✗ rejected", "x")])
def test_explicit_marks_with_notes_are_still_supported(value, expected):
    assert mark_of(value) == expected


def test_percentage_table_never_produces_verified_checklist_cards():
    context = _context(_percentage_rows())
    assert flag_matrix_report(context) == ([], "")
    report = validate_workbook_insights(WorkbookInsightReport(overview="", insights=[]), context)
    assert all("점검" not in item.fact and "기재된" not in item.fact for item in report.insights)


def test_canonical_sentence_cannot_certify_numeric_cells_as_marks():
    context = _context(_percentage_rows())
    bad = WorkbookInsight(
        title="Good 표시", fact="‘Good’는 기재된 6건이 0 6건입니다.",
        category="summary", severity="info", confidence=1,
        evidence=["'Observations'!B1:B7"],
    )
    # Defence in depth: even a buggy canonical generator cannot waive typing.
    assert _validate_insight(bad, workbook_evidence_index(context), [bad]) is None


def test_all_missing_or_zero_columns_do_not_establish_checklist_semantics():
    header = [_cell("A1", "Item"), _cell("B1", "Metric A"), _cell("C1", "Metric B")]
    records = [[_cell(f"A{r}", f"Item {r}"), _cell(f"B{r}", "0"), _cell(f"C{r}", "-")]
               for r in range(2, 8)]
    assert flag_matrix(header, records) is None


def test_unknown_filled_status_is_not_silently_dropped_from_distribution():
    header = [_cell("A1", "Item"), _cell("B1", "Check A"), _cell("C1", "Check B")]
    records = [[_cell(f"A{r}", f"Item {r}"), _cell(f"B{r}", "o"), _cell(f"C{r}", "x")]
               for r in range(2, 8)]
    records[-1][1]["value"] = "awaiting approval"
    _, run = flag_matrix(header, records)
    assert run[0][2] == {"o": 5, "awaiting approval": 1}
    assert sum(run[0][2].values()) == len(run[0][3])


@pytest.mark.parametrize("unknown", [.34, 4, "0.34", "34%", "-4"])
def test_numeric_values_in_a_mixed_column_do_not_become_status_categories(unknown):
    header = [_cell("A1", "Item"), _cell("B1", "Check A"), _cell("C1", "Check B")]
    records = [[_cell(f"A{r}", f"Item {r}"), _cell(f"B{r}", "o"), _cell(f"C{r}", "x")]
               for r in range(2, 8)]
    records[-1][1]["value"] = unknown
    assert flag_matrix(header, records) is None


def test_footer_is_not_an_unchecked_item_and_real_unmarked_item_is_retained():
    header = [_cell("A1", "ID"), _cell("B1", "Device"), _cell("C1", "Check A"), _cell("D1", "Check B")]
    records = [[_cell(f"A{r}", f"R-{r}"), _cell(f"B{r}", f"Device {r}"),
                _cell(f"C{r}", "✓"), _cell(f"D{r}", "✗")]
               for r in range(2, 8)]
    records += [[_cell("A8", "R-8"), _cell("B8", "Device 8")],
                [_cell("A9", "Source: maintenance team")],
                [_cell("A10", "Data collected annually")]]
    report = validate_workbook_insights(WorkbookInsightReport(overview="", insights=[]), _context([header, *records]))
    assert report.insights
    head = next(item for item in report.insights if "점검한 표" in item.fact)
    assert "7건을" in head.fact
    assert "6건이 점검됐고 1건(Device 8)" in head.fact
    assert "9건을" not in head.fact
    assert "'Observations'!A2:D2" in head.evidence
    assert all("9" not in ref and "10" not in ref for ref in head.evidence)


def test_single_identity_column_source_note_is_excluded_without_losing_unmarked_item():
    header = [_cell("A1", "Location"), _cell("B1", "Check A"), _cell("C1", "Check B")]
    records = [[_cell(f"A{r}", f"Location {r}"), _cell(f"B{r}", "o"), _cell(f"C{r}", "x")]
               for r in range(2, 8)]
    records += [[_cell("A8", "Location 8")], [_cell("A9", "Source: field survey")]]
    items, _ = flag_matrix_report(_context([header, *records]))
    assert "7건을" in items[0].fact
    assert "1건(Location 8)" in items[0].fact
