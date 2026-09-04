import re
from datetime import date, datetime
from xml.sax.saxutils import escape

from openpyxl.utils.datetime import to_excel

from app.agent.writeback.models import WritebackChange
from app.agent.writeback.package_xml import (
    _ElementSpan, _prefix, _update_attributes, _xml_elements,
)

INVALID_XML = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f]")


def _replace_cells(xml: bytes, changes: list[WritebackChange], epoch: datetime) -> bytes:
    cells: dict[str, _ElementSpan] = {}
    references = {change.reference.upper() for change in changes}
    if len(references) != len(changes):
        raise ValueError("중복된 변경 대상입니다.")
    for element in _xml_elements(xml, references):
        if element.name != "c":
            continue
        reference = element.attributes.get("r", "").upper()
        if reference in cells:
            raise ValueError("원본 셀 XML에 중복된 셀 주소가 있습니다.")
        cells[reference] = element
    edits = []
    for change in changes:
        element = cells.get(change.reference.upper())
        if element is None:
            raise ValueError("원본 셀 XML을 찾을 수 없습니다.")
        prefix = _prefix(element.qname)
        cell_type, body = _serialized_value(change.new_value, change.value_type, epoch, prefix)
        attrs = _update_attributes(element.raw_attributes, {"t": cell_type})
        preserved_body = xml[element.opening_end:element.closing_start]
        insertion = 0
        for child in sorted(element.value_children, key=lambda item: item.start, reverse=True):
            insertion = child.start - element.opening_end
            end = child.end - element.opening_end
            preserved_body = preserved_body[:insertion] + preserved_body[end:]
        updated_body = preserved_body[:insertion] + body.encode("utf-8") + preserved_body[insertion:]
        replacement = (
            b"<" + element.qname + attrs + b">"
            + updated_body + b"</" + element.qname + b">"
        )
        edits.append((element.start, element.end, replacement))
    parts = []
    offset = 0
    for start, end, replacement in sorted(edits):
        parts.extend((xml[offset:start], replacement))
        offset = end
    parts.append(xml[offset:])
    return b"".join(parts)


def _serialized_value(
    value: object, value_type: str, epoch: datetime, prefix: str = ""
) -> tuple[str | None, str]:
    if value is None or value_type == "blank":
        return None, ""
    if value_type == "formula":
        formula = str(value).strip()
        if not formula.startswith("="):
            raise ValueError("승인한 수식 형식이 올바르지 않습니다.")
        return None, f"<{prefix}f>{escape(formula[1:])}</{prefix}f>"
    if value_type in {"date", "datetime"}:
        try:
            temporal = (
                datetime.fromisoformat(str(value))
                if value_type == "datetime"
                else date.fromisoformat(str(value))
            )
        except ValueError as exception:
            raise ValueError("날짜는 YYYY-MM-DD 형식으로 입력해주세요.") from exception
        return "n", f"<{prefix}v>{to_excel(temporal, epoch)}</{prefix}v>"
    if isinstance(value, bool):
        return "b", f"<{prefix}v>{1 if value else 0}</{prefix}v>"
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return "n", f"<{prefix}v>{value}</{prefix}v>"
    text = str(value)
    if len(text) > 32_767 or INVALID_XML.search(text):
        raise ValueError("Excel 셀에 저장할 수 없는 문자열입니다.")
    escaped = escape(text)
    return "inlineStr", f'<{prefix}is><{prefix}t xml:space="preserve">{escaped}</{prefix}t></{prefix}is>'
