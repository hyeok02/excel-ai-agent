"""Interpret only positive definitions explicitly linked to the selected table."""
import re

from app.services.insights.display.record_labels import declared_record_label, header_words
from app.services.insights.narratives.narrative_values import reference


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
