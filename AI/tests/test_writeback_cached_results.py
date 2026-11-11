"""Formulas reading an approved cell get their recalculated result saved, only when provable."""
import math
import re
from io import BytesIO
from zipfile import ZipFile

from openpyxl import Workbook

from app.agent.query.index import build_workbook_data_index
from app.agent.writeback.editor import apply_writeback
from app.agent.writeback.models import WritebackChange


def _book(cached, extra=None):
    """A workbook whose formulas carry saved results, as Excel would save them."""
    book = Workbook()
    sheet = book.active
    sheet.title = "Sales"
    for row in (["Qty", "Price", "Total"], [2, 10, "=A2*B2"], [3, 5, "=A3*B3"], [None, None, "=SUM(C2:C3)"]):
        sheet.append(row)
    if extra:
        sheet["D2"] = extra
    output = BytesIO()
    book.save(output)
    source = ZipFile(BytesIO(output.getvalue()))
    target = BytesIO()
    with ZipFile(target, "w") as package:
        for info in source.infolist():
            data = source.read(info.filename)
            if info.filename == "xl/worksheets/sheet1.xml":
                for address, value in cached.items():
                    data = re.sub(rb'(<c r="' + address.encode() + rb'"[^>]*>)(<f>[^<]*</f>)(<v>[^<]*</v>)?',
                                  lambda m: m.group(1) + m.group(2) + b"<v>" + value.encode() + b"</v>", data)
            package.writestr(info, data)
    return target.getvalue()


def _values(content):
    index = build_workbook_data_index("s.xlsx", content, max_cells=math.inf, max_rows=math.inf)
    return {cell.reference: cell.value for row in index.rows for cell in row.cells}


CHANGE = WritebackChange(sheet_name="Sales", reference="B2", old_value=10, new_value=12, reason="r",
                         value_type="number")


def test_results_of_formulas_reading_the_change_are_saved_and_nothing_else_moves():
    content, manifest = apply_writeback("s.xlsx", _book({"C2": "20", "C3": "15", "C4": "35"}), [CHANGE])
    values = _values(content)
    assert (values["Sales!C2"], values["Sales!C3"], values["Sales!C4"]) == (24, 15, 39)
    assert manifest.verified and "cached_results" in {check.name for check in manifest.checks}
    sheet = ZipFile(BytesIO(content)).read("xl/worksheets/sheet1.xml")
    assert b"<f>A2*B2</f>" in sheet and b"<f>SUM(C2:C3)</f>" in sheet


def test_a_file_whose_saved_results_the_evaluator_cannot_reproduce_keeps_its_saved_results():
    content, manifest = apply_writeback("s.xlsx", _book({"C2": "999", "C3": "15", "C4": "35"}), [CHANGE])
    assert _values(content)["Sales!C2"] == 999 and manifest.verified
    assert "cached_results" not in {check.name for check in manifest.checks}


def test_a_text_result_reading_the_change_stops_every_refresh():
    book = _book({"C2": "20", "C3": "15", "C4": "35"}, extra='=IF(B2>11,"high","low")')
    content, manifest = apply_writeback("s.xlsx", book, [CHANGE])
    assert _values(content)["Sales!C2"] == 20 and manifest.verified


def test_a_workbook_without_formulas_is_returned_as_the_approved_edit_left_it():
    book = Workbook()
    book.active.title = "Sales"
    book.active.append([2, 10])
    output = BytesIO()
    book.save(output)
    change = CHANGE.model_copy(update={"reference": "B1"})
    content, manifest = apply_writeback("s.xlsx", output.getvalue(), [change])
    assert _values(content)["Sales!B1"] == 12 and manifest.verified
    assert "cached_results" not in {check.name for check in manifest.checks}
