"""Describe the selected record table, with citations for every added detail.

Descriptions must explicitly name this sheet/table. Other sheets, example links,
filenames and incidental category values cannot supply its business meaning.
"""
import re
from dataclasses import dataclass, field

from app.services.insights.display.record_labels import (
    declared_record_label, header_words, record_kind, record_subject, restricted_activity,
)
from app.services.insights.facts.fact_trends import date_value
from app.services.insights.narratives.narrative_values import reference


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


def _descriptions(context, names):
    """Accept explicit definitions, not unscoped documentation keyword hits."""
    for sheet in context.get("sheets", []):
        facts = sheet.get("business_facts", {})
        regions = facts.get("table_regions", [])
        rows = [row for region in regions for row in region.get("rows", [])]
        if not regions:
            rows = facts.get("table_rows", [])
        for row in rows:
            # A description is a short text row, not a transaction record.
            if len(row) > 2:
                continue
            for cell in row:
                text = cell.get("value")
                if not isinstance(text, str) or not cell.get("cell") or len(text) > 350:
                    continue
                if any(re.match(rf"^\s*{re.escape(name)}(?:\s*[:：]\s*|\s+sheet\s+)", text, re.I)
                       for name in names if name):
                    yield text, [reference(sheet.get("name", ""), cell["cell"])]


def _definition_body(text, scope_names):
    words = header_words(text, keep_case=True)
    for name in scope_names:
        words = re.sub(rf"^{re.escape(header_words(name))}(?:\s*[:：]\s*|\s+sheet\s+)", "", words, flags=re.I)
    return words


def _declared_subject(descriptions, scope_names, headers):
    """Read the declared subject of this exact table, never nearby examples.

    Restrict the grammar to positive definitions.  Contradictory definitions
    remain neutral, and unknown nouns are quoted rather than guessed from a
    filename or an incidental category value.
    """
    candidates = {}
    definitions = [_definition_body(text, scope_names) for text, _ in descriptions]
    if any(re.search(r"\b(?:not|no|non|except|excluding)\b|아닌|아님|제외", text, re.I)
           for text in definitions):
        return None
    for (text, refs), body in zip(descriptions, definitions):
        match = re.fullmatch(
            r"\s*(?:(?:has|contains|lists|provides|records|shows)\s+(?:(?:the|a|an)\s+)?)?"
            r"([\w][\w /&-]{1,90}?)\s+(?:data|records|transactions)"
            r"(?:\s+(?:for|from|of)\s+[^.;]+)?[.]?\s*", body, re.I,
        )
        if not match:
            continue
        noun = match[1].strip()
        # An operational qualifier is meaningful source information.  It may
        # be kept verbatim, but cannot be dropped by the simpler activity label.
        key = header_words(noun)
        candidates.setdefault(key, (noun, []))[1].extend(refs)
    if len(candidates) != 1:
        return None
    noun, refs = next(iter(candidates.values()))
    names = {header_words(cell["value"]) for cell in headers.values()}
    insurance = bool(names & {"insured value", "insurance premium", "sum insured", "보험가액", "보험료"})
    subject, kind = declared_record_label(noun, insurance=insurance)
    return subject, kind, refs


def _subject(text, scope_names):
    words = _definition_body(text, scope_names)
    title = re.fullmatch(r"(.+?)\s+(?:sales|purchases?)(?:\s+(?:data|records|orders))?", words, re.I)
    if title:
        noun = title.group(1)
        # Fiscal/technical qualifiers are not products or company names.
        if not re.search(r"\d|\b(?:data|table|tbl|monthly|annual|daily|quarterly|total|net|gross|sample)\b", noun, re.I):
            return noun
    korean = re.fullmatch(r"(.+?)\s*(?:판매|구매)(?:\s*(?:내역|현황|기록|자료))?", words)
    if korean and not re.search(r"\d|월별|연간|분기|일별|전체|샘플", korean[1]):
        return korean[1].strip()
    # Descriptions can identify the subject even if the sheet is named Data.
    company = re.search(r"\bfrom\s+(?:a\s+)?(?:fictional\s+)?([a-z][a-z ]{0,50}?)\s+company\b", words, re.I)
    return company[1].strip() if company else ""


def _examples(sheet, headers, records, kind):
    # Values are quoted verbatim: a Sales category must never become revenue.
    candidates = []
    for p, header in headers.items():
        word = header_words(header["value"])
        if word not in {"category", "product", "item", "분류", "제품", "상품", "품목"}:
            continue
        values = [row.get(p, {}).get("value") for row in records]
        if not all(isinstance(v, str) and v.strip() and len(v) <= 50 for v in values):
            continue
        unique = list(dict.fromkeys(values))
        candidates.append((word not in {"category", "분류"}, p, header, unique))
    if not candidates:
        return "", []
    _, p, header, values = min(candidates, key=lambda c: c[:2])
    labels = ", ".join(f"‘{v}’" for v in values[:3])
    labels += " 등" if len(values) > 3 else ""
    noun = "분류 항목" if header_words(header["value"]) in {"category", "분류"} else "품목"
    return (f"{noun}에는 {labels}{'이 있습니다' if len(values) > 3 else ' 항목이 있습니다'}.",
            [reference(sheet, header["cell"]),
             reference(sheet, f"{records[0][p]['cell']}:{records[-1][p]['cell']}")])


def _period(sheet, headers, records, kind):
    allowed = {"date", "transaction date", "날짜", "거래일"}
    allowed |= ({"sales date", "order date", "판매일", "주문일"} if kind == "판매 내역"
                else {"purchase date", "구매일"})
    candidates = [(p, c) for p, c in headers.items() if header_words(c["value"]) in allowed]
    if len(candidates) != 1:
        return "", []
    p, header = candidates[0]
    cells = [row.get(p, {}) for row in records]
    if not all(re.fullmatch(r"\d{4}-\d{2}-\d{2}(?:[T ].+)?", str(c.get("value", ""))) for c in cells):
        return "", []
    dates = [date_value(c.get("value")) for c in cells]
    if not all(dates):
        return "", []
    # Source-local calendar days, with no assumption about timezone conversion.
    days = [d.date() for d in dates]
    first, last = min(days), max(days)
    def label(d):
        return f"{d.year}년 {d.month}월 {d.day}일"
    span = label(first) if first == last else f"{label(first)}부터 {label(last)}까지"
    return span, [reference(sheet, header["cell"]),
                  reference(sheet, f"{cells[0]['cell']}:{cells[-1]['cell']}")]
