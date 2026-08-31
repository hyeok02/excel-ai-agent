import re
from io import BytesIO
from posixpath import normpath
from xml.sax.saxutils import escape
from zipfile import ZIP_DEFLATED, ZipFile

from defusedxml import ElementTree

from app.agent.writeback.models import WritebackChange

MAIN_NS = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"
DOC_REL_NS = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
PACKAGE_REL_NS = "http://schemas.openxmlformats.org/package/2006/relationships"
INVALID_XML = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f]")


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
                xml = _replace_cell(xml, change.reference, change.new_value)
            replacements[path] = xml.encode("utf-8")
        output = BytesIO()
        with ZipFile(output, "w", ZIP_DEFLATED) as target:
            for info in source.infolist():
                target.writestr(info, replacements.get(info.filename, source.read(info.filename)))
    return output.getvalue()


def changed_worksheet_paths(content: bytes, changes: list[WritebackChange]) -> set[str]:
    with ZipFile(BytesIO(content)) as archive:
        paths = _worksheet_paths(archive)
    return {paths[change.sheet_name] for change in changes}


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


def _replace_cell(xml: str, reference: str, value: object) -> str:
    cell_pattern = re.compile(
        rf'(<c\b(?=[^>]*\br="{re.escape(reference.upper())}")(?P<attrs>[^>]*)>)'
        rf'(?P<body>.*?)(</c>)',
        re.DOTALL,
    )
    match = cell_pattern.search(xml)
    if match is None:
        raise ValueError("원본 셀 XML을 찾을 수 없습니다.")
    attrs = re.sub(r'\s+t="[^"]*"', "", match.group("attrs"))
    cell_type, body = _serialized_value(value)
    replacement = f'<c{attrs} t="{cell_type}">{body}</c>'
    return xml[: match.start()] + replacement + xml[match.end() :]


def _serialized_value(value: object) -> tuple[str, str]:
    if isinstance(value, bool):
        return "b", f"<v>{1 if value else 0}</v>"
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return "n", f"<v>{value}</v>"
    text = str(value)
    if len(text) > 32_767 or INVALID_XML.search(text):
        raise ValueError("Excel 셀에 저장할 수 없는 문자열입니다.")
    escaped = escape(text)
    return "inlineStr", f'<is><t xml:space="preserve">{escaped}</t></is>'
