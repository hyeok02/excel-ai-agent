from copy import copy
from datetime import datetime
from io import BytesIO
from posixpath import normpath
from zipfile import ZIP_DEFLATED, ZipFile

from defusedxml import ElementTree
from openpyxl.utils.datetime import CALENDAR_MAC_1904, CALENDAR_WINDOWS_1900

from app.agent.writeback.models import WritebackChange
from app.agent.writeback.package_cells import _replace_cells
from app.agent.writeback.package_xml import MAIN_NS, _prefix, _update_attributes, _xml_elements

DOC_REL_NS = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
PACKAGE_REL_NS = "http://schemas.openxmlformats.org/package/2006/relationships"
WORKBOOK_PATH = "xl/workbook.xml"


def patch_workbook_package(content: bytes, changes: list[WritebackChange]) -> bytes:
    with ZipFile(BytesIO(content)) as source:
        paths = _worksheet_paths(source)
        epoch = _epoch(source)
        replacements: dict[str, bytes] = {}
        grouped: dict[str, list[WritebackChange]] = {}
        for change in changes:
            if change.sheet_name not in paths:
                raise ValueError("존재하지 않는 시트입니다.")
            grouped.setdefault(paths[change.sheet_name], []).append(change)
        for path, sheet_changes in grouped.items():
            replacements[path] = _replace_cells(source.read(path), sheet_changes, epoch)
        replacements[WORKBOOK_PATH] = _request_recalculation(
            source.read(WORKBOOK_PATH)
        )
        output = BytesIO()
        with ZipFile(output, "w", ZIP_DEFLATED) as target:
            target.comment = source.comment
            for info in source.infolist():
                target.writestr(
                    copy(info), replacements.get(info.filename, source.read(info.filename))
                )
    return output.getvalue()

def changed_worksheet_paths(content: bytes, changes: list[WritebackChange]) -> set[str]:
    with ZipFile(BytesIO(content)) as archive:
        paths = _worksheet_paths(archive)
    changed = {paths[change.sheet_name] for change in changes}
    changed.add(WORKBOOK_PATH)
    return changed

def _worksheet_paths(archive: ZipFile) -> dict[str, str]:
    workbook = ElementTree.fromstring(archive.read("xl/workbook.xml"))
    relations = ElementTree.fromstring(archive.read("xl/_rels/workbook.xml.rels"))
    targets = {
        item.attrib["Id"]: item.attrib["Target"]
        for item in relations.findall(f"{{{PACKAGE_REL_NS}}}Relationship")
    }
    return {
        sheet.attrib["name"]: _part_path(targets[sheet.attrib[f"{{{DOC_REL_NS}}}id"]])
        for sheet in workbook.findall(f".//{{{MAIN_NS}}}sheet")
    }


def _part_path(target: str) -> str:
    normalized = target.lstrip("/")
    return normpath(normalized if normalized.startswith("xl/") else "xl/" + normalized)


def _epoch(archive: ZipFile) -> datetime:
    workbook = ElementTree.fromstring(archive.read(WORKBOOK_PATH))
    properties = workbook.find(f"{{{MAIN_NS}}}workbookPr")
    uses_1904 = properties is not None and properties.get("date1904") in {"1", "true"}
    return CALENDAR_MAC_1904 if uses_1904 else CALENDAR_WINDOWS_1900


def _request_recalculation(xml: bytes) -> bytes:
    attributes = {
        "calcMode": "auto",
        "fullCalcOnLoad": "1",
        "forceFullCalc": "1",
    }
    elements = _xml_elements(xml)
    calculation = next((item for item in elements if item.name == "calcPr"), None)
    if calculation:
        attrs = _update_attributes(calculation.raw_attributes, attributes)
        replacement = b"<" + calculation.qname + attrs + b"/>"
        return xml[:calculation.start] + replacement + xml[calculation.end:]
    workbook = next((item for item in elements if item.name == "workbook"), None)
    if workbook is None or workbook.empty:
        raise ValueError("원본 워크북 XML을 찾을 수 없습니다.")
    tag = f'<{_prefix(workbook.qname)}calcPr calcMode="auto" fullCalcOnLoad="1" forceFullCalc="1"/>'.encode()
    return xml[:workbook.closing_start] + tag + xml[workbook.closing_start:]
