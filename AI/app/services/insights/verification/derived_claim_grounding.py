"""Require source labels or computed evidence for derived numeric prose."""
import re
from decimal import Decimal, InvalidOperation

from app.services.insights.verification.numeric_validation import NUMBER_PATTERN, numbers
from app.services.insights.verification.reference_matching import matching_references
from app.services.insights.verification.validation_index import REFERENCE_PATTERN, extract_references
from app.services.insights.verification.trend_claims import (
    scoped_changes, supported_change_numbers, same_endpoint_periods,
)

STATISTICS = (
    re.compile(r"평균|\b(?:average|mean)\b", re.I),
    re.compile(r"합계|총합|\b(?:sum|total)\b", re.I),
    re.compile(r"최대|최댓값|\b(?:max|maximum)\b", re.I),
    re.compile(r"최소|최솟값|\b(?:min|minimum)\b", re.I),
)
INCREASE = re.compile(r"증가|늘었|늘어|높아|상승|\bincreas\w*|\brose\b", re.I)
DECREASE = re.compile(r"감소|줄었|줄어|낮아|하락|\bdecreas\w*|\bfell\b", re.I)
SUPERLATIVE = re.compile(r"가장|제일|\b(?:largest|smallest|highest|lowest|most|least)\b", re.I)
QUOTED = re.compile(r'"([^"\n]+)"|“([^”\n]+)”|‘([^’\n]+)’|「([^」\n]+)」')
VALUE = r"-?\d[\d,]*(?:\.\d+)?"
ENDPOINTS = re.compile(
    rf"(?<![\d,.])(?P<old>{VALUE}\s*[A-Za-z가-힣%]*)에서\s*"
    rf"[^.!?;]*?(?<![\d,.])(?P<new>{VALUE}\s*[A-Za-z가-힣%]*?)(?:으로|로)"
)


def grounded_derivation(text, source_text, references, index_changes, metric_labels=()) -> bool:
    """This checks derivations, not lexical/numeric grounding (checked separately)."""
    text = REFERENCE_PATTERN.sub(" ", text)
    sources = [str(source).strip() for source in source_text]
    if text.strip() in sources:
        return True
    prose = _remove_source_quotes(text, sources)
    if SUPERLATIVE.search(prose):
        return False  # Rankings require the independently computed canonical fact.
    for statistic in STATISTICS:
        if statistic.search(prose) and not any(statistic.search(source) for source in sources):
            return False
    from app.services.insights.verification.relation_grounding import CLAUSES
    for clause in CLAUSES.split(prose):
        rising, falling = bool(INCREASE.search(clause)), bool(DECREASE.search(clause))
        endpoints = list(ENDPOINTS.finditer(clause))
        if not rising and not falling and not endpoints:
            continue
        if rising and falling:
            return False
        covered = [change for change in index_changes if _covered(change, references)]
        changes = scoped_changes(clause, covered, metric_labels)
        if not changes or not all(_consistent_direction(change, rising, falling) for change in changes):
            return False
        if not supported_change_numbers(clause, changes, source_text):
            return False
        if not all(any(_same_endpoints(match, change) for change in changes) for match in endpoints):
            return False
    return True


def _remove_source_quotes(text, sources):
    def replace(match):
        quote = next(part for part in match.groups() if part is not None)
        if any(quote in source for source in sources):
            return " "
        return match.group(0)
    return QUOTED.sub(replace, text)


def _covered(change, references):
    if not isinstance(change, dict):
        return False
    evidence = change.get("evidence")
    if not isinstance(evidence, list) or not evidence:
        return False
    cited = [extract_references(str(item)) for item in evidence]
    if any(not parsed for parsed in cited):
        return False
    return all(
        any(matching_references(reference, {required}) for reference in references)
        for required in set().union(*cited)
    )


def _decimal(value):
    if isinstance(value, bool) or value is None:
        return None
    try:
        parsed = Decimal(str(value).replace(",", ""))
        return parsed if parsed.is_finite() else None
    except InvalidOperation:
        return None


def _consistent_direction(change, rising, falling):
    old, new, delta = (_decimal(change.get(key)) for key in (
        "earliest_value", "latest_value", "change",
    ))
    if old is None or new is None or delta is None:
        return False
    if abs((new - old) - delta) > Decimal("0.000001"):
        return False
    return (not rising or delta > 0) and (not falling or delta < 0)


def _same_endpoints(match, change):
    return same_endpoint_periods(match, change) and all(
        _decimal(change.get(key)) in _signed_values(match.group(group))
        for group, key in (("old", "earliest_value"), ("new", "latest_value"))
    )


def _signed_values(value):
    candidates = numbers(value)
    return {-item for item in candidates} if value.lstrip().startswith("-") else candidates
