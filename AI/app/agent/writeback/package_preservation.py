"""Prove every XML byte outside approved values and recalculation is unchanged."""
from collections import defaultdict

from app.agent.writeback.package_editor import WORKBOOK_PATH, _worksheet_paths
from app.agent.writeback.package_xml import _xml_elements


def unchanged_content(original, modified, changes):
    paths = _worksheet_paths(original)
    grouped = defaultdict(set)
    for change in changes:
        grouped[paths[change.sheet_name]].add(change.reference.upper())
    return all(_without_values(original.read(path), refs) == _without_values(modified.read(path), refs)
               for path, refs in grouped.items()) and (
        _without_calculation(original.read(WORKBOOK_PATH))
        == _without_calculation(modified.read(WORKBOOK_PATH))
    )


def _without_values(xml, references):
    spans = [span for span in _xml_elements(xml, references) if span.name == "c"]
    if {span.attributes.get("r", "").upper() for span in spans} != references:
        raise ValueError("보존 검증에서 승인한 원본 셀을 찾을 수 없습니다.")
    edits = []
    for span in spans:
        body = xml[span.opening_end:span.closing_start]
        for child in sorted(span.value_children, key=lambda item: item.start, reverse=True):
            body = body[:child.start - span.opening_end] + body[child.end - span.opening_end:]
        attributes = sorted((name, value) for name, value in span.attributes.items() if name != "t")
        skeleton = repr((span.qname, attributes, body)).encode("utf-8")
        edits.append((span.start, span.end, skeleton))
    return _replace(xml, edits)


def _without_calculation(xml):
    return _replace(xml, [(span.start, span.end, b"") for span in _xml_elements(xml)
                          if span.name == "calcPr"])


def _replace(xml, edits):
    for start, end, replacement in sorted(edits, reverse=True):
        xml = xml[:start] + replacement + xml[end:]
    return xml
