"""Write recalculated formula results into worksheet XML, touching only each cell's <v>."""
from copy import copy
from io import BytesIO
from zipfile import ZipFile

from app.agent.writeback.package_editor import _worksheet_paths
from app.agent.writeback.package_xml import _xml_elements


def _patched(content, updates):
    with ZipFile(BytesIO(content)) as source:
        paths = _worksheet_paths(source)
        grouped = {}
        for ref, value in updates.items():
            sheet, address = ref.rsplit("!", 1)
            grouped.setdefault(paths[sheet], {})[address.upper()] = value
        replacements = {path: _with_results(source.read(path), values) for path, values in grouped.items()}
        output = BytesIO()
        with ZipFile(output, "w") as target:
            target.comment = source.comment
            for info in source.infolist():
                target.writestr(copy(info), replacements.get(info.filename, source.read(info.filename)))
    return output.getvalue()


def _with_results(xml, values):
    edits = []
    for span in _xml_elements(xml, set(values)):
        address = span.attributes.get("r", "").upper()
        if span.name != "c" or address not in values:
            continue
        if span.attributes.get("t", "n") != "n":
            raise ValueError("숫자가 아닌 결과 형식의 수식은 결과값을 바꾸지 않습니다.")
        formula = next((child for child in span.value_children if child.name == "f"), None)
        cached = next((child for child in span.value_children if child.name == "v"), None)
        prefix = span.qname.rsplit(b":", 1)[0] + b":" if b":" in span.qname else b""
        text = _text(values.pop(address))
        tag = b"<" + prefix + b"v>" + text + b"</" + prefix + b"v>"
        if cached is not None:
            edits.append((cached.start, cached.end, tag))
        elif formula is not None:
            edits.append((formula.end, formula.end, tag))
        else:
            raise ValueError("수식 셀 XML을 찾을 수 없습니다.")
    if values:
        raise ValueError("결과값을 바꿀 수식 셀을 찾지 못했습니다.")
    parts, position = [], 0
    for start, end, replacement in sorted(edits):
        parts.extend((xml[position:start], replacement))
        position = end
    parts.append(xml[position:])
    return b"".join(parts)


def _text(value):
    number = float(value)
    return (str(int(number)) if number.is_integer() and abs(number) < 1e15 else repr(number)).encode()
