"""Question/source alignment, independent of a model-authored answer."""
import re

from app.agent.query.references import extract_references, matching_references, normalize_reference
from app.agent.query.search_terms import search_terms
from app.agent.query.translated_evidence import translated_evidence_sources
from app.agent.query.verified_insight_constraints import requested_identifiers_match
from app.agent.query.claim_constraints import observation_constraints_match

GENERIC = {"값", "셀", "시트", "원본", "항목", "질문", "설명", "상태", "현재", "대상", "기간",
           "value", "cell", "sheet", "status", "tell", "please", "does", "about"}


def claim_scope_matches(question, evidence, available, value_reference=None):
    references = {normalize_reference(f"{item.sheet_name}!{item.reference}") for item in evidence}
    asked = extract_references(question)
    scoped = {value_reference} if value_reference else references
    if asked and not all(any(matching_references(bound, {ref}) for bound in asked) for ref in scoped):
        return False
    names = {item.sheet_name.casefold() for item in available.values()}
    named = {name for name in names if re.search(rf"(?<!\w){re.escape(name)}(?!\w)", question.casefold())}
    if named and any(item.sheet_name.casefold() not in named for item in evidence):
        return False
    source = " ".join(str(value) for item in evidence
                      for value in (item.value, item.description, item.sheet_name))
    source += " " + " ".join(translated_evidence_sources(evidence))
    if not observation_constraints_match(question, evidence, source):
        return False
    labels = {str(value).strip().casefold() for item in available.values()
              for value in (item.value, item.description) if isinstance(value, str)
              and 2 <= len(value.strip()) <= 160 and not value.strip().isdigit()}
    named_labels = {label for label in labels if _mentioned(label, question.casefold())}
    named_labels = {label for label in named_labels
                    if not any(label != longer and label in longer for longer in named_labels)}
    if any(label not in source.casefold() for label in named_labels):
        return False
    if not requested_identifiers_match(question.casefold(), source.casefold()):
        return False
    years = set(re.findall(r"(?<!\d)(?:19|20)\d{2}(?!\d)", question))
    if years and not years <= set(re.findall(r"(?<!\d)(?:19|20)\d{2}(?!\d)", source)):
        return False
    # Direct addresses are already an exact source selector. Otherwise require
    # a content-bearing overlap, never merely words such as "value" or "cell".
    terms = set(search_terms(question)) - GENERIC
    return bool(asked or named_labels or any(term in source.casefold() for term in terms))


def _mentioned(label, question):
    if label.isascii():
        return bool(re.search(rf"(?<![a-z0-9_]){re.escape(label)}(?![a-z0-9_])", question))
    return label in question
