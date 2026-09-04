from io import BytesIO
from xml.etree import ElementTree
from zipfile import ZIP_DEFLATED, ZipFile

import pytest

from app.agent.writeback.models import WritebackChange
from app.agent.writeback.package_editor import (
    DOC_REL_NS,
    MAIN_NS,
    PACKAGE_REL_NS,
    patch_workbook_package,
)


def _package(prefix: str, *, empty: bool = False, calc: bool = True) -> bytes:
    p = f"{prefix}:" if prefix else ""
    namespace = f'xmlns:{prefix}="{MAIN_NS}"' if prefix else f'xmlns="{MAIN_NS}"'
    cell = f"<{p}c r='A1' s='0' t = 'n' evil:note=' t=\"s\" > 보존'"
    cell += "/>" if empty else f"><{p}v>1</{p}v></{p}c>"
    sheet = (
        f'<{p}worksheet {namespace} xmlns:evil="urn:foreign">'
        f'<{p}sheetData><{p}row r="1">'
        '<evil:c r="A1"><evil:v>999</evil:v></evil:c>'
        f'{cell}<{p}c r="B1"><{p}v>2</{p}v></{p}c>'
        f'</{p}row></{p}sheetData>'
        '<evil:extLst marker="원본"><evil:c r="A1"/></evil:extLst>'
        f'</{p}worksheet>'
    )
    calc_xml = f"<{p}calcPr calcId='123' calcMode = 'manual'></{p}calcPr>" if calc else ""
    workbook = (
        f'<{p}workbook {namespace} xmlns:r="{DOC_REL_NS}" xmlns:evil="urn:foreign">'
        f'<{p}workbookPr date1904="1"/>'
        f'<{p}sheets><{p}sheet name="Sheet" sheetId="1" r:id="rId1"/></{p}sheets>'
        '<evil:calcPr calcMode="manual"/>'
        f'{calc_xml}</{p}workbook>'
    )
    relationships = (
        f'<Relationships xmlns="{PACKAGE_REL_NS}">'
        '<Relationship Id="rId1" Target="worksheets/sheet1.xml"/>'
        '</Relationships>'
    )
    stream = BytesIO()
    with ZipFile(stream, "w", ZIP_DEFLATED) as archive:
        archive.writestr("xl/workbook.xml", workbook.encode())
        archive.writestr("xl/_rels/workbook.xml.rels", relationships.encode())
        archive.writestr("xl/worksheets/sheet1.xml", sheet.encode())
        archive.writestr("xl/styles.xml", b"opaque Hancom styles preserved exactly")
        archive.writestr("xl/vbaProject.bin", b"opaque VBA preserved exactly")
    return stream.getvalue()


def _change(value: object = 3, value_type: str = "number") -> WritebackChange:
    return WritebackChange(
        sheet_name="Sheet", reference="A1", old_value=1,
        new_value=value, value_type=value_type, reason="검증된 변경",
    )


@pytest.mark.parametrize("prefix", ["", "x", "arbitrary"])
@pytest.mark.parametrize("empty", [False, True])
@pytest.mark.parametrize("calc", [False, True])
def test_patches_only_standard_cells_and_calculation_settings(prefix, empty, calc):
    original = _package(prefix, empty=empty, calc=calc)
    modified = patch_workbook_package(original, [_change()])
    with ZipFile(BytesIO(original)) as before, ZipFile(BytesIO(modified)) as after:
        assert before.namelist() == after.namelist()
        for name in before.namelist():
            if name not in {"xl/workbook.xml", "xl/worksheets/sheet1.xml"}:
                assert before.read(name) == after.read(name)
        sheet_xml = after.read("xl/worksheets/sheet1.xml")
        sheet = ElementTree.fromstring(sheet_xml)
        cell = sheet.find(f"{{{MAIN_NS}}}sheetData/{{{MAIN_NS}}}row/{{{MAIN_NS}}}c")
        assert cell.find(f"{{{MAIN_NS}}}v").text == "3"
        assert cell.attrib["s"] == "0"
        assert cell.attrib["{urn:foreign}note"] == ' t="s" > 보존'
        assert b'<evil:c r="A1"><evil:v>999</evil:v></evil:c>' in sheet_xml
        assert '<evil:extLst marker="원본"><evil:c r="A1"/></evil:extLst>'.encode() in sheet_xml
        workbook_xml = after.read("xl/workbook.xml")
        assert b'<evil:calcPr calcMode="manual"/>' in workbook_xml
        workbook = ElementTree.fromstring(workbook_xml)
        settings = workbook.findall(f"{{{MAIN_NS}}}calcPr")
        assert len(settings) == 1
        assert settings[0].attrib["calcMode"] == "auto"
        assert settings[0].attrib["fullCalcOnLoad"] == "1"
        assert settings[0].attrib["forceFullCalc"] == "1"
        if calc:
            assert settings[0].attrib["calcId"] == "123"


@pytest.mark.parametrize(
    "value,value_type,tag,expected",
    [("=SUM(B1:B2)", "formula", "f", "SUM(B1:B2)"),
     ("한글 & <값>", "text", "is", None),
     (True, "boolean", "v", "1"),
     ("1904-01-02", "date", "v", "1.0")],
)
def test_new_cell_children_keep_the_original_namespace(value, value_type, tag, expected):
    modified = patch_workbook_package(_package("x"), [_change(value, value_type)])
    with ZipFile(BytesIO(modified)) as archive:
        root = ElementTree.fromstring(archive.read("xl/worksheets/sheet1.xml"))
    child = root.find(f"{{{MAIN_NS}}}sheetData/{{{MAIN_NS}}}row/{{{MAIN_NS}}}c/{{{MAIN_NS}}}{tag}")
    assert child is not None
    if expected is not None:
        assert child.text == expected
    else:
        assert child.find(f"{{{MAIN_NS}}}t").text == value


def test_rejects_dtd_even_if_it_does_not_declare_entities():
    from app.agent.writeback.package_editor import _request_recalculation

    with pytest.raises(ValueError, match="DTD"):
        _request_recalculation(f'<!DOCTYPE workbook><workbook xmlns="{MAIN_NS}"></workbook>'.encode())


def test_rejects_foreign_namespace_cell_instead_of_editing_it():
    from app.agent.writeback.package_editor import _replace_cells
    from openpyxl.utils.datetime import CALENDAR_WINDOWS_1900

    xml = (
        f'<worksheet xmlns="{MAIN_NS}" xmlns:evil="urn:foreign">'
        '<sheetData><row><evil:c r="A1"><evil:v>1</evil:v></evil:c></row></sheetData>'
        '</worksheet>'
    ).encode()
    with pytest.raises(ValueError, match="원본 셀 XML"):
        _replace_cells(xml, [_change()], CALENDAR_WINDOWS_1900)


def test_preserves_extensions_and_comments_inside_the_approved_cell():
    from app.agent.writeback.package_editor import _replace_cells
    from openpyxl.utils.datetime import CALENDAR_WINDOWS_1900

    extension = '<x:extLst><evil:v>보존</evil:v></x:extLst>'.encode()
    xml = (
        f'<x:worksheet xmlns:x="{MAIN_NS}" xmlns:evil="urn:foreign">'
        '<x:sheetData><x:row><x:c r="A1">'
        '<!--comment--><x:f>SUM(B1:B2)</x:f><x:v>1</x:v>'
    ).encode() + extension + b'</x:c></x:row></x:sheetData></x:worksheet>'
    modified = _replace_cells(xml, [_change(5)], CALENDAR_WINDOWS_1900)
    assert extension in modified
    assert b'<!--comment--><x:v>5</x:v>' in modified
    assert b'<x:f>' not in modified
