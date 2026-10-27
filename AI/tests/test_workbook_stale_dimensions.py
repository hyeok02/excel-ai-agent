"""Exporter dimension hints must not hide real cells from Q&A/writeback."""
from io import BytesIO
import re
from zipfile import ZipFile

import pytest
from openpyxl import Workbook

from app.agent.query import index
from tests.support.writeback_target_fixtures import proposal


def _stale_workbook(sheet_name, dimension):
    book = Workbook()
    sheet = book.active
    sheet.title = sheet_name
    sheet.append(["Period", "Amount"])
    sheet.append(["Cycle A", 12])
    sheet["Z8"] = 62.2
    sheet["AA8"] = "=Z8*2"
    output = BytesIO()
    book.save(output)
    book.close()
    patched = BytesIO()
    with ZipFile(BytesIO(output.getvalue())) as source, ZipFile(patched, "w") as target:
        for item in source.infolist():
            content = source.read(item.filename)
            if item.filename == "xl/worksheets/sheet1.xml":
                replacement = f'<dimension ref="{dimension}"/>'.encode() if dimension else b""
                content = re.sub(rb'<dimension\s+ref="[^"]+"\s*/>', replacement, content)
            target.writestr(item, content)
    return patched.getvalue()


@pytest.mark.parametrize("sheet_name", ["Observed Series", "집계_임의이름"])
@pytest.mark.parametrize("dimension", ["A1", "A1:B2", None])
def test_index_reads_real_rows_not_stale_dimension_hint(sheet_name, dimension):
    result = index.build_workbook_data_index("renamed-export.xlsx", _stale_workbook(sheet_name, dimension))
    cells = {cell.address: cell for row in result.rows for cell in row.cells}
    assert cells["Z8"].value == 62.2
    assert cells["AA8"].formula == "=Z8*2"
    assert result.indexed_cell_count == 6
    assert result.truncated is False
    assert [row.row_number for row in result.rows] == [1, 2, 8]


def test_stale_dimension_does_not_disable_cell_budget_or_claim_completeness(monkeypatch):
    monkeypatch.setattr(index, "MAX_INDEXED_CELLS", 5)
    result = index.build_workbook_data_index("limited.xlsx", _stale_workbook("Series", "A1"))
    assert result.indexed_cell_count == 5
    assert result.truncated is True
    assert result.truncated_sheet_names == frozenset({"Series"})
    assert result.rows[-1].cells[-1].address == "Z8"


def test_stale_dimension_does_not_disable_nonempty_row_budget(monkeypatch):
    monkeypatch.setattr(index, "MAX_ROWS_PER_SHEET", 2)
    result = index.build_workbook_data_index("limited.xlsx", _stale_workbook("Series", "A1"))
    assert result.indexed_cell_count == 4
    assert result.truncated is True
    assert result.truncated_sheet_names == frozenset({"Series"})


@pytest.mark.parametrize("reference,value,expected", [
    ("Z8", 63.2, "ready"), ("B2", 63.2, "blocked"),
    ("AA8", 63.2, "blocked"), ("Z8", 99, "blocked"),
])
def test_real_cell_edit_after_stale_dimension_still_checks_scope_and_value(reference, value, expected):
    body = proposal("'Observed Series'!Z8을 63.2로 수정해줘",
                    [("Observed Series", reference, value)],
                    _stale_workbook("Observed Series", "A1"))
    assert body["status"] == expected, body
    if expected == "ready":
        assert body["changes"][0]["old_value"] == 62.2
