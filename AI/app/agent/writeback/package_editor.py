import re
from datetime import date, datetime
from io import BytesIO
from posixpath import normpath
from xml.sax.saxutils import escape
from zipfile import ZIP_DEFLATED, ZipFile

from defusedxml import ElementTree
from openpyxl.utils.datetime import CALENDAR_MAC_1904, CALENDAR_WINDOWS_1900, to_excel

from app.agent.writeback.models import WritebackChange

MAIN_NS = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"
DOC_REL_NS = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
PACKAGE_REL_NS = "http://schemas.openxmlformats.org/package/2006/relationships"
INVALID_XML = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f]")
WORKBOOK_PATH = "xl/workbook.xml"

def patch_workbook_package(content: bytes, changes: list[WritebackChange]) -> bytes:
    with ZipFile(BytesIO(content)) as source:
        paths = _worksheet_paths(source)
        replacements: dict[str, bytes] = {}
        grouped: dict[str, list[WritebackChange]] = {}
        for change in changes:
            if change.sheet_name not in paths:
                raise ValueError("존재하지 않는 시트입니다.")
            grouped.setdefault(paths[change.sheet_name], []).append(change)
        for path, sheet_changes in grouped.items():
            xml = source.read(path).decode("utf-8")
            for change in sheet_changes:
                xml = _replace_cell(
                    xml,
                    change.reference,
                    change.new_value,
                    change.value_type,
                    _epoch(source),
                )
            replacements[path] = xml.encode("utf-8")
        replacements[WORKBOOK_PATH] = _request_recalculation(
            source.read(WORKBOOK_PATH).decode("utf-8")
        ).encode("utf-8")
        output = BytesIO()
        with ZipFile(output, "w", ZIP_DEFLATED) as target:
            for info in source.infolist():
                target.writestr(
                    info, replacements.get(info.filename, source.read(info.filename))
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


def _replace_cell(
    xml: str, reference: str, value: object, value_type: str, epoch: datetime
) -> str:
    cell_pattern = re.compile(
        rf'(<c\b(?=[^>]*\br="{re.escape(reference.upper())}")(?P<attrs>[^>]*)>)'
        rf'(?P<body>.*?)(</c>)',
        re.DOTALL,
    )
    match = cell_pattern.search(xml)
    if match is None:
        raise ValueError("원본 셀 XML을 찾을 수 없습니다.")
    attrs = re.sub(r'\s+t="[^"]*"', "", match.group("attrs"))
    cell_type, body = _serialized_value(value, value_type, epoch)
    type_attribute = f' t="{cell_type}"' if cell_type else ""
    replacement = f"<c{attrs}{type_attribute}>{body}</c>"
    return xml[: match.start()] + replacement + xml[match.end() :]


def _serialized_value(
    value: object, value_type: str, epoch: datetime
) -> tuple[str | None, str]:
    if value is None or value_type == "blank":
        return None, ""
    if value_type == "formula":
        formula = str(value).strip()
        if not formula.startswith("="):
            raise ValueError("승인한 수식 형식이 올바르지 않습니다.")
        return None, f"<f>{escape(formula[1:])}</f>"
    if value_type in {"date", "datetime"}:
        try:
            temporal = (
                datetime.fromisoformat(str(value))
                if value_type == "datetime"
                else date.fromisoformat(str(value))
            )
        except ValueError as exception:
            raise ValueError("날짜는 YYYY-MM-DD 형식으로 입력해주세요.") from exception
        return "n", f"<v>{to_excel(temporal, epoch)}</v>"
    if isinstance(value, bool):
        return "b", f"<v>{1 if value else 0}</v>"
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return "n", f"<v>{value}</v>"
    text = str(value)
    if len(text) > 32_767 or INVALID_XML.search(text):
        raise ValueError("Excel 셀에 저장할 수 없는 문자열입니다.")
    escaped = escape(text)
    return "inlineStr", f'<is><t xml:space="preserve">{escaped}</t></is>'


def _epoch(archive: ZipFile) -> datetime:
    workbook = archive.read(WORKBOOK_PATH)
    return CALENDAR_MAC_1904 if re.search(rb'date1904="(?:1|true)"', workbook) else CALENDAR_WINDOWS_1900


def _request_recalculation(xml: str) -> str:
    attributes = {
        "calcMode": "auto",
        "fullCalcOnLoad": "1",
        "forceFullCalc": "1",
    }
    match = re.search(
        r"<calcPr\b(?P<attrs>[^>]*?)(?:/>|>.*?</calcPr>)", xml, re.DOTALL
    )
    if match:
        attrs = match.group("attrs")
        for name, value in attributes.items():
            if re.search(rf'\b{name}="[^"]*"', attrs):
                attrs = re.sub(rf'\b{name}="[^"]*"', f'{name}="{value}"', attrs)
            else:
                attrs += f' {name}="{value}"'
        replacement = f"<calcPr{attrs}/>"
        return xml[: match.start()] + replacement + xml[match.end() :]
    return xml.replace(
        "</workbook>",
        '<calcPr calcMode="auto" fullCalcOnLoad="1" forceFullCalc="1"/></workbook>',
    )
