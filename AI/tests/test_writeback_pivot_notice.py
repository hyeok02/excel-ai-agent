"""An edit warns that pivot tables keep cached totals until they are refreshed."""
from io import BytesIO
from types import SimpleNamespace
from zipfile import ZipFile

from app.agent.writeback.pivot_notice import pivot_sheets, with_pivot_notice

PIVOT = "http://schemas.openxmlformats.org/officeDocument/2006/relationships/pivotTable"


def _package(pivot=True):
    stream = BytesIO()
    with ZipFile(stream, "w") as package:
        package.writestr("xl/workbook.xml", '<workbook><sheets><sheet name="Data" sheetId="1" r:id="rId1"/>'
                                            '<sheet name="R&amp;D Pivot" sheetId="2" r:id="rId2"/></sheets></workbook>')
        package.writestr("xl/_rels/workbook.xml.rels", '<Relationships><Relationship Id="rId1" Target="worksheets/sheet1.xml"/>'
                                                      '<Relationship Id="rId2" Target="/xl/worksheets/sheet2.xml"/></Relationships>')
        if pivot:
            package.writestr("xl/worksheets/_rels/sheet2.xml.rels",
                             f'<Relationships><Relationship Id="rId1" Type="{PIVOT}" Target="../pivotTables/p1.xml"/></Relationships>')
    return stream.getvalue()


def test_sheets_holding_pivot_tables_are_named_only_when_cells_change() -> None:
    assert pivot_sheets(_package()) == ["R&D Pivot"]
    assert pivot_sheets(_package(pivot=False)) == [] and pivot_sheets(b"not a zip") == []
    proposal = SimpleNamespace(changes=[1], limitations=[], model_copy=lambda update: SimpleNamespace(**update))
    assert "R&D Pivot" in with_pivot_notice(proposal, _package()).limitations[0]
    blocked = SimpleNamespace(changes=[], limitations=[])
    assert with_pivot_notice(blocked, _package()) is blocked
