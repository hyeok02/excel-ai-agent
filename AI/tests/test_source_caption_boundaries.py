"""Caption and qualification scope must survive extra unrelated tables."""
from app.services.insights.models import WorkbookInsight
from app.services.insights.narratives.source_context import source_table_context
from app.services.insights.narratives.source_qualifications import source_qualifications


def _sheet(cells, name="Data"):
    rows = [[{"cell": address, "value": value} for address, value in cells.items()]]
    return {"name": name, "business_facts": {"table_rows": rows}}


def _item(*evidence):
    return WorkbookInsight(title="변화", fact="2025년 10에서 2026년 12로 증가했습니다.",
                           evidence=list(evidence), category="metric", severity="info", confidence=1)


def _base():
    return {"A1": "Table 2.3 Average Price of Goods",
            "A2": "Year", "B2": "Price", "A3": 2025, "B3": 10, "A4": 2026, "B4": 12}


def test_single_table_caption_preserves_source_reference():
    context = {"sheets": [_sheet(_base())]}
    assert source_table_context(context, _item("'Data'!B3:B4")) == (
        "Table 2.3 Average Price of Goods", ["'Data'!A1"])


def test_caption_preserves_its_explicit_provisional_qualification():
    cells = _base() | {"A1": "Table 3.2: Provisional Territorial greenhouse gas emissions by gas, UK 1991-2026"}
    context = {"sheets": [_sheet(cells)]}
    assert source_table_context(context, _item("'Data'!B3:B4")) == (cells["A1"], ["'Data'!A1"])


def test_title_continuation_keeps_subject_and_period_instead_of_only_scope():
    cells = {"A1": "Table 8.4 Average Price of Electricity to Ultimate Customers",
             "A2": "by State, August 2026 and 2025 (Cents per Kilowatthour)",
             "A3": "Region", "B3": "2025", "C3": "2026", "A4": "Total", "B4": 12, "C4": 15}
    context = {"sheets": [_sheet(cells)]}
    caption, refs = source_table_context(context, _item("'Data'!B4:C4"))
    assert caption == cells["A1"] + " " + cells["A2"]
    assert refs == ["'Data'!A1", "'Data'!A2"]


def test_unequal_numeric_evidence_on_two_sheets_does_not_choose_dominant_caption():
    second = _sheet({"A1": "Table 8 Inventory by Location", "B3": 50}, "Other")
    context = {"sheets": [_sheet(_base()), second]}
    assert source_table_context(context, _item("'Data'!B3:B4", "'Other'!B3")) == ("", [])


def test_non_numeric_other_sheet_evidence_does_not_block_single_numeric_caption():
    context = {"sheets": [_sheet(_base()), _sheet({"A1": "Metadata"}, "Other")]}
    assert source_table_context(context, _item("'Data'!B3:B4", "'Other'!A1"))[0] == _base()["A1"]


def test_new_header_after_prior_values_cannot_inherit_old_tables_title():
    cells = _base() | {"A10": "Department", "B10": "Employees", "A11": "Service", "B11": 5,
                       "A12": "Engineering", "B12": 8}
    context = {"sheets": [_sheet(cells)]}
    assert source_table_context(context, _item("'Data'!B11:B12")) == ("", [])


def test_new_dimension_header_with_numeric_year_columns_breaks_old_caption():
    cells = _base() | {"A10": "Region", "B10": 2025, "C10": 2026,
                       "A11": "North", "B11": 20, "C11": 30}
    context = {"sheets": [_sheet(cells)]}
    assert source_table_context(context, _item("'Data'!B11:C11")) == ("", [])


def test_new_table_with_its_own_caption_remains_readable():
    cells = _base() | {"A9": "Table 9 Number of Employees by Department",
                       "A10": "Department", "B10": "Employees", "A11": "Service", "B11": 5,
                       "A12": "Engineering", "B12": 8}
    context = {"sheets": [_sheet(cells)]}
    caption, refs = source_table_context(context, _item("'Data'!B11:B12"))
    assert caption == cells["A9"]
    assert refs == ["'Data'!A9"]


def test_same_sheet_comparison_across_two_captioned_tables_has_no_unique_caption():
    cells = _base() | {"A9": "Table 9 Number of Employees by Department", "B11": 5}
    context = {"sheets": [_sheet(cells)]}
    assert source_table_context(context, _item("'Data'!B3:B4", "'Data'!B11")) == ("", [])


def test_single_cell_annual_or_year_to_date_sections_keep_parent_table_title():
    cells = _base() | {"A10": "Year to Date", "A11": 2025, "B11": 5, "A12": 2026, "B12": 8}
    context = {"sheets": [_sheet(cells)]}
    assert source_table_context(context, _item("'Data'!B11:B12"))[0] == cells["A1"]


def test_missing_value_row_does_not_look_like_a_fresh_table_header():
    cells = _base() | {"A5": "North", "B5": "NM", "A6": "South", "B6": 15}
    context = {"sheets": [_sheet(cells)]}
    assert source_table_context(context, _item("'Data'!B6"))[0] == cells["A1"]


def test_left_tables_caption_cannot_name_right_hand_table():
    cells = _base() | {"F2": "Department", "G2": "Employees", "F3": "Service", "G3": 5,
                       "F4": "Engineering", "G4": 8}
    context = {"sheets": [_sheet(cells)]}
    assert source_table_context(context, _item("'Data'!G3:G4")) == ("", [])


def test_side_by_side_tables_keep_status_notes_in_their_own_column_block():
    cells = _base() | {"A6": "Note: Values for 2026 are preliminary.",
                       "F2": "Year", "G2": "Employees", "F3": 2025, "G3": 5,
                       "F4": 2026, "G4": 8, "F6": "Values for 2026 are final."}
    context = {"sheets": [_sheet(cells)]}
    assert source_qualifications(context, _item("'Data'!B3:B4")) == (
        "2026년 수치는 원본에서 잠정치로 표시되어 있습니다.", ["'Data'!A6"])
    assert source_qualifications(context, _item("'Data'!G3:G4")) == (
        "2026년 수치는 원본에서 확정치로 표시되어 있습니다.", ["'Data'!F6"])


def test_first_tables_status_note_does_not_apply_to_second_table_same_year():
    cells = _base() | {"A6": "Values for 2026 are preliminary.",
                       "A9": "Table 9 Net Generation by Fuel", "A10": "Year", "B10": "Value",
                       "A11": 2025, "B11": 100, "A12": 2026, "B12": 120}
    context = {"sheets": [_sheet(cells)]}
    assert source_qualifications(context, _item("'Data'!B11:B12")) == ("", [])
    assert source_qualifications(context, _item("'Data'!B3:B4")) == (
        "2026년 수치는 원본에서 잠정치로 표시되어 있습니다.", ["'Data'!A6"])


def test_second_tables_status_note_does_not_apply_backwards_to_first_table():
    cells = _base() | {"A9": "Table 9 Net Generation by Fuel", "A10": "Year", "B10": "Value",
                       "A11": 2025, "B11": 100, "A12": 2026, "B12": 120,
                       "A15": "Values for 2026 are preliminary."}
    context = {"sheets": [_sheet(cells)]}
    assert source_qualifications(context, _item("'Data'!B3:B4")) == ("", [])
    assert source_qualifications(context, _item("'Data'!B11:B12"))[1] == ["'Data'!A15"]


def test_same_sheet_second_table_without_title_has_its_own_note_scope():
    cells = _base() | {"A6": "Values for 2026 are final.",
                       "A10": "Year", "B10": "Output", "A11": 2025, "B11": 100,
                       "A12": 2026, "B12": 120, "A15": "Values for 2026 are preliminary."}
    context = {"sheets": [_sheet(cells)]}
    assert source_qualifications(context, _item("'Data'!B11:B12")) == (
        "2026년 수치는 원본에서 잠정치로 표시되어 있습니다.", ["'Data'!A15"])
