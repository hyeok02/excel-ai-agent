import re
from dataclasses import dataclass, field
from xml.parsers.expat import ExpatError, ParserCreate

MAIN_NS = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"
START_TAG = re.compile(
    rb"<(?P<name>[^\s/>]+)(?P<attrs>(?:[^>'\"]|'[^']*'|\"[^\"]*\")*?)(?P<empty>/?)>"
)
ATTRIBUTE = re.compile(rb"\s+(?P<name>[^\s=]+)\s*=\s*(?:\"[^\"]*\"|'[^']*')")


@dataclass
class _ElementSpan:
    name: str
    attributes: dict[str, str]
    start: int
    opening_end: int
    qname: bytes
    raw_attributes: bytes
    empty: bool
    closing_start: int = 0
    end: int = 0
    value_children: list["_ElementSpan"] = field(default_factory=list)

def _prefix(qname: bytes) -> str:
    return qname.rsplit(b":", 1)[0].decode("utf-8") + ":" if b":" in qname else ""


def _update_attributes(raw: bytes, updates: dict[str, str | None]) -> bytes:
    pending = {key.encode(): value for key, value in updates.items()}

    def replace(match: re.Match[bytes]) -> bytes:
        name = match.group("name")
        if name not in pending:
            return match.group(0)
        value = pending.pop(name)
        return b" " + name + b'="' + value.encode() + b'"' if value is not None else b""

    result = ATTRIBUTE.sub(replace, raw)
    return result + b"".join(
        b" " + name + b'="' + value.encode() + b'"'
        for name, value in pending.items() if value is not None
    )


def _xml_elements(xml: bytes, references: set[str] | None = None) -> list[_ElementSpan]:
    """Locate only standard OOXML targets without serializing extension markup."""
    parser = ParserCreate(namespace_separator="}")
    stack: list[tuple[str, _ElementSpan | None]] = []
    elements: list[_ElementSpan] = []
    accepted_paths = {
        tuple(f"{MAIN_NS}}}{name}" for name in path)
        for path in (("worksheet", "sheetData", "row", "c"), ("workbook",), ("workbook", "calcPr"))
    }
    accepted_paths.update(
        tuple(f"{MAIN_NS}}}{name}" for name in ("worksheet", "sheetData", "row", "c", child))
        for child in ("f", "v", "is")
    )

    def start(name: str, attributes: dict[str, str]) -> None:
        path = tuple(item[0] for item in stack) + (name,) if len(stack) < 5 else ()
        span = None
        selected = path in accepted_paths
        if selected and name == f"{MAIN_NS}}}c" and references is not None:
            selected = attributes.get("r", "").upper() in references
        if selected and name in {f"{MAIN_NS}}}{tag}" for tag in ("f", "v", "is")}:
            selected = stack[-1][1] is not None
        if selected:
            offset = parser.CurrentByteIndex
            match = START_TAG.match(xml, offset)
            if match is None:
                raise ValueError("원본 Excel XML 태그를 읽을 수 없습니다.")
            span = _ElementSpan(
                name.rsplit("}", 1)[-1], attributes, offset, match.end(),
                match.group("name"), match.group("attrs"), bool(match.group("empty")),
            )
        stack.append((name, span))

    def end(_name: str) -> None:
        _, span = stack.pop()
        if span is not None:
            span.closing_start = span.opening_end if span.empty else parser.CurrentByteIndex
            span.end = span.opening_end if span.empty else xml.index(b">", span.closing_start) + 1
            if span.name in {"f", "v", "is"}:
                stack[-1][1].value_children.append(span)
            else:
                elements.append(span)

    def reject_dtd(*_args: object) -> None:
        raise ValueError("DTD 또는 엔터티가 포함된 Excel XML은 수정할 수 없습니다.")

    parser.StartElementHandler = start
    parser.EndElementHandler = end
    parser.StartDoctypeDeclHandler = reject_dtd
    parser.EntityDeclHandler = reject_dtd
    parser.ExternalEntityRefHandler = reject_dtd
    try:
        parser.Parse(xml, True)
    except ExpatError as exception:
        raise ValueError("올바른 Excel XML이 아닙니다.") from exception
    return elements
