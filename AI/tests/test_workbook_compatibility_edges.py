from copy import copy
from io import BytesIO
from xml.etree import ElementTree as ET
from zipfile import ZipFile

from fastapi.testclient import TestClient

from app.agent.writeback import apply_writeback
from app.agent.writeback.models import WritebackChange
from app.main import app
from app.services.workbook_loading import close_workbook, load_workbook_for_reading
from app.services.workbook_parser import parse_workbook
from tests.support.compatibility_workbook import compatibility_workbook, replace_part
from tests.support.workbook_api_fixtures import upload


def test_utf16_compatibility_styles_are_resolved() -> None:
    original = compatibility_workbook()
    with ZipFile(BytesIO(original)) as archive:
        styles = ET.fromstring(archive.read("xl/styles.xml"))
    utf16 = replace_part(original, "xl/styles.xml", ET.tostring(styles, encoding="utf-16"))
    assert parse_workbook("sales.xlsx", utf16) == parse_workbook("sales.xlsx", original)


def test_malformed_style_xml_returns_400_without_compatibility_marker() -> None:
    broken = replace_part(compatibility_workbook(), "xl/styles.xml", b"<styleSheet><invalid>")
    response = TestClient(app).post("/api/v1/workbooks/summary", files=upload("broken.xlsx", broken))
    assert response.status_code == 400
    assert response.json()["detail"] == "올바른 Excel 파일이 아닙니다."


def test_compatibility_writeback_preserves_vba_payload_bytes() -> None:
    payload = b"synthetic-vba-preservation-fixture-not-executable"
    original = compatibility_workbook()
    stream = BytesIO()
    with ZipFile(BytesIO(original)) as source, ZipFile(stream, "w") as package:
        for info in source.infolist():
            data = source.read(info.filename)
            if info.filename == "[Content_Types].xml":
                data = data.replace(
                    b"application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml",
                    b"application/vnd.ms-excel.sheet.macroEnabled.main+xml",
                ).replace(
                    b"</Types>",
                    b'<Override PartName="/xl/vbaProject.bin" '
                    b'ContentType="application/vnd.ms-office.vbaProject"/></Types>',
                )
            package.writestr(copy(info), data)
        package.writestr("xl/vbaProject.bin", payload)
    original = stream.getvalue()
    modified, manifest = apply_writeback(
        "sales.xlsm", original,
        [WritebackChange(sheet_name="매출현황", reference="B2", old_value=10,
                         new_value=12, value_type="number", reason="정정")],
    )
    assert manifest.verified
    with ZipFile(BytesIO(original)) as source, ZipFile(BytesIO(modified)) as result:
        assert result.read("xl/vbaProject.bin") == payload
        assert source.read("xl/styles.xml") == result.read("xl/styles.xml")
    workbook = load_workbook_for_reading(modified, keep_vba=True)
    vba_archive = workbook.vba_archive
    close_workbook(workbook)
    assert vba_archive.fp is None
