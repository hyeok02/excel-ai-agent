"""Describe the selected record table, with citations for every added detail.

Descriptions must explicitly name this sheet/table. Other sheets, example links,
filenames and incidental category values cannot supply its business meaning.
"""
import re
from dataclasses import dataclass, field

from app.services.insights.display.record_labels import header_words, record_kind, record_subject, restricted_activity
from app.services.insights.narratives.narrative_values import reference
from app.services.insights.narratives.record_context_definitions import _descriptions, _definition_body, _declared_subject, _subject
from app.services.insights.narratives.record_context_details import _examples, _period


@dataclass
class RecordContext:
    kind: str = "기록"
    subject: str = ""
    examples: str = ""
    period: str = ""
    sample: bool = False
    evidence: list[str] = field(default_factory=list)

    @property
    def name(self):
        return " ".join(filter(None, [self.subject, self.kind]))

    def lead(self, count):
        when = f"{self.period}의 " if self.period else ""
        example = "예시 " if self.sample else ""
        details = f" {self.examples}" if self.examples else ""
        return f"이 파일은 {when}{self.name} {count:,}건을 정리한 {example}자료입니다.{details}"


def describe_records(context, sheet, headers, records):
    name = sheet.get("name", "")
    result = RecordContext()
    # A sheet name applies to the selected table only when there is no other
    # declared table. A matching named table can supply a more precise scope.
    tables = sheet.get("table_samples", [])
    table_count = max(sheet.get("table_count", 0) or 0, len(tables))
    scope_names = [] if table_count > 1 else [name]
    first = next(iter(headers.values()))["cell"]
    last = list(records[-1].values())[-1]["cell"]
    for table in tables:
        if str(table.get("reference", "")).replace("$", "") == f"{first}:{last}":
            scope_names.append(table.get("name", ""))
    source_refs = [reference(name, c["cell"]) for c in headers.values()]
    descriptions = list(_descriptions(context, scope_names))
    meanings = [(text, source_refs) for text in scope_names]
    # A definition's exact table-name prefix only links it to this table; it
    # must not contribute an activity word (e.g. Sales: Purchase records).
    meanings += [(_definition_body(text, scope_names), refs) for text, refs in descriptions]
    kinds = {record_kind(text, headers) for text, _ in meanings} - {"기록"}
    # Conflicting sales/purchase sources stay neutral rather than picking one.
    if len(kinds) == 1 and not any(restricted_activity(text) for text, _ in meanings):
        result.kind = kinds.pop()
        result.evidence += source_refs
        subjects = {}
        for text, refs in meanings:
            if record_kind(text, headers) != result.kind:
                continue
            result.evidence += refs
            subject = _subject(text, scope_names)
            if subject:
                subjects.setdefault(header_words(subject), subject)
        if len(subjects) == 1:
            result.subject = record_subject(next(iter(subjects.values())))
    # Definitions can describe any business record, not only price/quantity
    # transactions.  Keep this separate from sales classification: an insurance
    # value is not revenue, and a policy expiry is not a transaction period.
    if result.kind == "기록":
        declared = _declared_subject(descriptions, scope_names, headers)
        if declared:
            result.subject, result.kind, refs = declared
            result.evidence += [*source_refs, *refs]
    for text, refs in descriptions:
        if re.search(r"\b(?:fictional|sample|synthetic)\b|가상|예시|예제", text, re.I) and not re.search(
            r"\b(?:not|non|no)\b|아닌|아님", text, re.I
        ):
            result.sample = True
            result.evidence += refs
    # A clear business subject already answers what this file contains. Only
    # add concrete values when that subject is absent; avoid cluttering prose.
    if not result.subject:
        result.examples, example_refs = _examples(name, headers, records, result.kind)
        result.evidence += example_refs
    if result.kind in {"판매 내역", "구매 내역"}:
        result.period, period_refs = _period(name, headers, records, result.kind)
        result.evidence += period_refs
    result.evidence = list(dict.fromkeys(result.evidence))
    return result
