"""Aggregate thresholds are verified separately from source-row predicates."""
import re
from decimal import Decimal

from app.agent.query.tabular_advanced_language import SHARE, COUNT, DISTINCT
from app.agent.query.tabular_request_grouping import _source_tokens, _STAT
from app.agent.query.tabular_request_literals import without_literals
from app.agent.query.tabular_having_units import source_threshold
from app.agent.query.tabular_quantity import parse_quantity as _number

_NUMBER = r"-?\d[\d,]*(?:\.\d+)?(?:\s*[십백천만억조](?:\s*\d[\d,]*(?:\.\d+)?\s*[십백천만억조]?)?)*"
_CURRENCY = r"원|달러|유로|엔|파운드|USD|EUR|KRW|JPY|GBP|[$€£₩¥]"
_QUANTITY = (rf"(?P<currency_before>{_CURRENCY})?\s*(?P<number>{_NUMBER})\s*"
             rf"(?P<magnitude>thousands?|millions?|billions?|trillions?)?\s*"
             rf"(?P<currency>{_CURRENCY})?\s*(?P<unit>%|퍼센트|percent)?")
_OPS = {"이상": "greater_than_or_equal", "초과": "greater_than", "넘는": "greater_than",
        "넘은": "greater_than", "이하": "less_than_or_equal", "미만": "less_than",
        "보다 큰": "greater_than", "보다 작은": "less_than", "같은": "equals",
        ">=": "greater_than_or_equal", "≥": "greater_than_or_equal", "<=": "less_than_or_equal",
        "≤": "less_than_or_equal", ">": "greater_than", "<": "less_than", "=": "equals",
        "!=": "not_equals", "≠": "not_equals", "at least": "greater_than_or_equal",
        "at most": "less_than_or_equal", "more than": "greater_than", "greater than": "greater_than",
        "above": "greater_than", "less than": "less_than", "below": "less_than", "equal to": "equals"}
_PREFIX = r">=|<=|!=|≥|≤|≠|>|<|=|at least|at most|greater than|more than|less than|above|below|equal to"
_SUFFIX = r"이상|초과|넘는|넘은|이하|미만|보다\s*큰|보다\s*작은|같은"
_PATTERNS = [re.compile(rf"{_QUANTITY}\s*(?P<op>{_SUFFIX})", re.I),
             re.compile(rf"(?P<op>{_PREFIX})\s*{_QUANTITY}", re.I)]


def without_checked_having(text, plan, table):
    """Return only row-predicate text; None means an omitted/invented HAVING."""
    conditions = getattr(plan, "having", ())
    masked, identifiers = _source_tokens(text, table)
    if masked is None:
        return None if conditions else text
    checked, removals = set(), []
    for match in _matches(without_literals(text)):
        before, _ = _source_tokens(text[:match.start()], table)
        if before is None:
            return None
        context = _aggregate_context(before, plan, identifiers)
        if context is None:
            continue
        column, target = context
        number = _number(match.group("number"))
        value = None if number is None else source_threshold(number, match, table, column, target)
        if value is None:
            return None
        operation = " ".join(match.group("op").casefold().split())
        operation = operation.replace("보다큰", "보다 큰").replace("보다작은", "보다 작은")
        requested = (column, target, _OPS[operation], value, bool(match.group("unit")))
        found = [position for position, condition in enumerate(conditions)
                 if _condition(condition) == requested]
        if not found:
            return None
        checked.update(found)
        markers = list(re.finditer(_STAT + "|" + SHARE.pattern + "|" + COUNT.pattern,
                                   without_literals(text[:match.start()]), re.I))
        start = markers[-1].start() if markers else match.start()
        suffix = re.match(r"(?:인|이고|이며)?", text[match.end():]).end()
        removals.append((start, match.end() + suffix))
    if len(checked) != len(conditions):
        return None
    if re.search(r"\bhaving\b", masked, re.I) and not checked:
        return None
    # Preserve exact original offsets, including repeated identical thresholds.
    for start, end in reversed(removals):
        text = text[:start] + " " * (end - start) + text[end:]
    return text


def _matches(text):
    found = sorted((match for pattern in _PATTERNS for match in pattern.finditer(text)), key=lambda m: m.start())
    return [match for position, match in enumerate(found)
            if not any(other.start() <= match.start() and other.end() >= match.end()
                       for other in found[:position])]


def _aggregate_context(before, plan, identifiers):
    if not getattr(plan, "group_by", ()):
        return None
    markers = list(re.finditer(_STAT + "|" + SHARE.pattern + "|" + COUNT.pattern, before, re.I))
    if not markers:
        return None
    marker = markers[-1]
    gap = before[marker.end():]
    # Another source column after an aggregate starts a separate row condition.
    after_field = re.fullmatch(r"\s*(?:of\s+)?§(\d+)§\s*", gap, re.I)
    if after_field and plan.operation == "numeric_summary":
        return identifiers[int(after_field.group(1))], "aggregate"
    if len(gap) > 45 or re.search(r"§\d+§|[.;!?]|행|rows?\b", gap, re.I):
        return None
    if SHARE.fullmatch(marker.group()):
        return None, "share"
    if COUNT.fullmatch(marker.group()):
        return None, "aggregate"
    columns = list(re.finditer(r"§(\d+)§", before[:marker.start()]))
    if not columns or marker.start() - columns[-1].end() > 30:
        return None
    column = identifiers[int(columns[-1].group(1))]
    return column, "aggregate"


def _condition(condition):
    return (condition.column_id, condition.target, condition.operator,
            Decimal(str(condition.value)), condition.value_unit == "percent")
