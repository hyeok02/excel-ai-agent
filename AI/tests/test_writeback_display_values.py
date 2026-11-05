"""A change card shows each number the way the source cell's format shows it in Excel."""
from types import SimpleNamespace

from app.agent.writeback.display_values import shown, with_displays
from app.agent.writeback.models import WritebackChange, WritebackContextCell, WritebackRelatedCell
from tests.test_writeback_year_columns import _propose


def test_percent_cells_read_as_percentages_on_the_card():
    change = _propose("Attack의 2019년 값을 1.3%로 바꿔줘", "1.3%")["changes"][0]
    assert (change["old_display"], change["new_display"]) == ("3.3%", "1.3%")
    assert change["old_stored"] is None and change["new_stored"] is None
    assert [(cell["reference"], cell["display"]) for cell in change["context_cells"]][:2] == [
        ("C3", "3.9%"), ("E3", "2.7%")]


def test_general_numbers_drop_floating_point_noise_and_text_has_no_display():
    assert shown(1.8699999999999999, "General") == "1.87"
    assert shown(12345678901.0, "General") == "12345678901"
    assert shown("Cookies", "General") is None and shown(True, "General") is None


class Lookup:
    def __init__(self, formats):
        self.formats = formats

    def cell(self, sheet_name, reference):
        found = self.formats.get((sheet_name, reference))
        return SimpleNamespace(number_format=found) if found else None


def _change(old, new, **extra):
    return WritebackChange(sheet_name="S", reference="B2", old_value=old, new_value=new, reason="r", **extra)


def test_hidden_digits_of_the_new_value_are_given_as_stored_values():
    cell = SimpleNamespace(sheet_name="S", number_format="$#,##0.00")
    change = with_displays(_change(1.87, 2.057), cell, Lookup({}))
    assert (change.old_display, change.new_display, change.new_stored) == ("$1.87", "$2.06", "2.057")
    percent = SimpleNamespace(sheet_name="S", number_format="0.0%")
    same = with_displays(_change(0.0331, 0.033), percent, Lookup({}))
    assert (same.old_display, same.new_display) == ("3.3%", "3.3%")
    assert (same.old_stored, same.new_stored) == ("3.31%", "3.3%")


def test_neighbours_and_related_cells_use_their_own_formats():
    cell = SimpleNamespace(sheet_name="S", number_format="0.0%")
    change = _change(0.03, 0.05, context_cells=[WritebackContextCell(reference="C2", value=1234.6)],
                     related_cells=[WritebackRelatedCell(sheet_name="T", reference="D2", current_value=0.03,
                                                         suggested_value=0.05, kind="mirror", reason="같은 값")])
    change = with_displays(change, cell, Lookup({("S", "C2"): "#,##0", ("T", "D2"): "0%"}))
    assert change.context_cells[0].display == "1,235"
    assert (change.related_cells[0].current_display, change.related_cells[0].suggested_display) == ("3%", "5%")


def test_the_reading_names_the_value_as_the_cell_will_show_it():
    body = _propose("Attack의 2019년 값을 1.3%로 바꿔줘", 0.013)
    assert "‘2019’ 값을 1.3%(으)로 바꾸는" in body["limitations"][0]
