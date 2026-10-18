"""Bounded OOXML metadata reads; no macros, links, expressions, or user writes."""
from io import BytesIO
from pathlib import PurePosixPath
from xml.etree.ElementTree import ParseError
from zipfile import BadZipFile, ZipFile

from defusedxml.ElementTree import fromstring
from defusedxml.common import DefusedXmlException

from app.agent.query.formula_reference_metadata import FormulaName, FormulaTable, ReferenceMetadata

_MAIN = "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}"
_REL = "{http://schemas.openxmlformats.org/officeDocument/2006/relationships}"
MAX_METADATA_BYTES = 8 * 1024 * 1024
MAX_METADATA_PART_BYTES = 4 * 1024 * 1024
MAX_METADATA_ITEMS = 2048


class MetadataLimit(ValueError):
    pass


class PackageReader:
    def __init__(self, archive):
        self.archive, self.used = archive, 0

    def xml(self, path):
        entries = [info for info in self.archive.infolist() if info.filename == path]
        if len(entries) != 1:
            raise ValueError("missing or ambiguous package part")
        size = entries[0].file_size
        self.used += size
        if size > MAX_METADATA_PART_BYTES or self.used > MAX_METADATA_BYTES:
            raise MetadataLimit()
        return fromstring(self.archive.read(entries[0]), forbid_dtd=True)

    def relationships(self, path):
        part = PurePosixPath(path)
        rel_path = str(part.parent / "_rels" / (part.name + ".rels"))
        if rel_path not in self.archive.namelist():
            return {}
        result = {}
        for rel in self.xml(rel_path):
            key, target = rel.get("Id"), rel.get("Target", "")
            if not key or key in result:
                raise ValueError("ambiguous relationship")
            if rel.get("TargetMode") == "External":
                result[key] = (None, rel.get("Type", ""))
                continue
            if "\\" in target or ":" in target:
                raise ValueError("invalid relationship")
            components = []
            for segment in str(part.parent / target).split("/") if not target.startswith("/") else target[1:].split("/"):
                if segment == "..":
                    if not components:
                        raise ValueError("outside package")
                    components.pop()
                elif segment not in ("", "."):
                    components.append(segment)
            result[key] = ("/".join(components), rel.get("Type", ""))
        return result


def read_reference_metadata(content: bytes, selected: set[str]) -> ReferenceMetadata:
    try:
        with ZipFile(BytesIO(content)) as archive:
            reader = PackageReader(archive)
            workbook = reader.xml("xl/workbook.xml")
            sheets = list(workbook.find(f"{_MAIN}sheets"))
            if len(sheets) > MAX_METADATA_ITEMS:
                raise MetadataLimit()
            allowed = frozenset(sheet.get("name") for sheet in sheets
                                if sheet.get("name") in selected)
            names = _names(workbook, sheets)
            relationships = reader.relationships("xl/workbook.xml")
            tables = []
            for sheet in sheets:
                if sheet.get("name") not in allowed:
                    continue
                path, kind = relationships[sheet.get(f"{_REL}id")]
                if not path or not kind.endswith("/worksheet"):
                    raise ValueError("invalid sheet source")
                tables.extend(_tables(reader, path, sheet.get("name")))
                if len(tables) + len(names) > MAX_METADATA_ITEMS:
                    raise MetadataLimit()
            return ReferenceMetadata(tuple(names), tuple(tables), allowed)
    except MetadataLimit:
        return ReferenceMetadata(unavailable="resource_limit")
    except (BadZipFile, KeyError, TypeError, ValueError, ParseError, DefusedXmlException, OSError):
        return ReferenceMetadata(unavailable="unsupported_reference")


def _names(workbook, sheets):
    definitions = workbook.find(f"{_MAIN}definedNames")
    if definitions is None:
        return []
    if len(definitions) > MAX_METADATA_ITEMS:
        raise MetadataLimit()
    names = []
    for item in definitions:
        scope = item.get("localSheetId")
        if scope is not None and (not scope.isdecimal() or int(scope) >= len(sheets)):
            raise ValueError("invalid name scope")
        names.append(FormulaName(item.get("name", ""), item.text or "",
                                 sheets[int(scope)].get("name") if scope is not None else None,
                                 item.get("hidden", "0").lower() not in ("0", "false")))
    return names


def _tables(reader, path, sheet):
    parts = reader.xml(path).find(f"{_MAIN}tableParts")
    if parts is None:
        return []
    relationships = reader.relationships(path)
    tables = []
    for part in parts:
        target, kind = relationships[part.get(f"{_REL}id")]
        if not target or not kind.endswith("/table"):
            raise ValueError("invalid table source")
        root = reader.xml(target)
        if root.tag != f"{_MAIN}table":
            raise ValueError("invalid table part")
        entries = list(root.find(f"{_MAIN}tableColumns"))
        columns = tuple(column.get("name", "") for column in entries)
        tables.append(FormulaTable(root.get("displayName", ""), sheet, root.get("ref", ""), columns,
                                   int(root.get("headerRowCount", "1")), int(root.get("totalsRowCount", "0")),
                                   tuple(i for i, column in enumerate(entries) if column.find(f"{_MAIN}calculatedColumnFormula") is not None),
                                   tuple(i for i, column in enumerate(entries) if column.find(f"{_MAIN}totalsRowFormula") is not None
                                         or column.get("totalsRowFunction", "none") != "none")))
    return tables
