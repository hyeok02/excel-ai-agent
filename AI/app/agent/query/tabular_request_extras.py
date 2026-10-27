"""Reject population-reducing filters that have no subject in the request."""
import re

from app.services.insights.display.glossary import translate
from app.agent.query.blank_predicate_language import PRESENT_VALUE
from app.agent.query.tabular_request_literals import source_headers, without_literals

_BLANK = re.compile(r"빈칸|공백|비어\s*있|누락|\b(?:blank|empty|missing|null)\b", re.I)
_NEGATIVE_BLANK = re.compile(r"빈칸.*(?:아닌|제외)|공백.*(?:아닌|제외)|비어\s*있지|\bnon[- ]?(?:blank|empty)\b|\bnot\s+(?:blank|empty|null)\b", re.I)


def extra_filters_supported(text, plan, table):
    blanks = _blank_polarities(text, table)
    for condition in plan.filters:
        if condition.operator in {"is_blank", "not_blank"}:
            if condition.operator not in blanks.get(condition.column_id, set()):
                return False
        elif isinstance(condition.value, bool):
            words = r"\btrue\b|참" if condition.value else r"\bfalse\b|거짓"
            if not re.search(words, text, re.I):
                return False
        elif isinstance(condition.value, str) and not _numeric_text(condition.value):
            if not _stated_subject(text, condition.value):
                from app.agent.query.tabular_total_scope import whole_total_filter_supported
                if whole_total_filter_supported(text, plan, table, condition):
                    continue
                # An unknown translation is not an independently checked binding.
                # Arbitrary remaining words cannot authorize a model-only filter.
                return False
    return True


def _blank_polarities(text, table):
    """Presence/exclusion wording belongs to its field, never every filter.

    For example A populated AND B blank has opposite polarities. A global
    'populated' match must neither reject B blank nor authorize C populated.
    """
    headers = source_headers(text, table)
    bindings = {}
    for column, header in headers:
        stop = min((other.start() for _, other in headers if other.start() >= header.end()),
                   default=len(text))
        clause = without_literals(text[header.end():stop])
        present = bool(PRESENT_VALUE.search(clause))
        if _BLANK.search(clause) or present:
            operator = "not_blank" if _NEGATIVE_BLANK.search(clause) or present else "is_blank"
            bindings.setdefault(column, set()).add(operator)
    # Prefix wording is unambiguous only when it names exactly one field.
    named = {column for column, _ in headers}
    if not bindings and len(named) == 1:
        prefix = without_literals(text[:min(header.start() for _, header in headers)])
        present = bool(PRESENT_VALUE.search(prefix))
        if _BLANK.search(prefix) or present:
            bindings[next(iter(named))] = {
                "not_blank" if _NEGATIVE_BLANK.search(prefix) or present else "is_blank",
            }
    return bindings


def _stated_subject(text, value):
    if re.search(_literal(value.strip()), text, re.I):
        return True
    translated = translate(value)
    if translated and translated in text:
        return True
    words = re.findall(r"[A-Za-z0-9]+|[가-힣]+", value)
    suffixes = {"and", "the", "of", "inc", "incorporated", "ltd", "limited", "llc", "plc", "corp", "corporation"}
    words = [word for word in words if word.casefold() not in suffixes]
    return bool(words) and all(re.search(rf"(?<![A-Za-z0-9]){re.escape(word)}(?![A-Za-z0-9])", text, re.I)
                               for word in words)


def _numeric_text(value):
    return bool(re.fullmatch(r"-?\d[\d,.]*", value.strip()))


def _literal(value):
    boundary = "A-Za-z0-9가-힣" if re.fullmatch(r"[가-힣]+", value) else "A-Za-z0-9"
    return rf"(?<![{boundary}]){re.escape(value)}(?![A-Za-z0-9])"
