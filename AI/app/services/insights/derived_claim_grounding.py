"""Require source labels or computed evidence for derived numeric prose."""
import re
from decimal import Decimal, InvalidOperation

from app.services.insights.numeric_validation import NUMBER_PATTERN, numbers
from app.services.insights.reference_matching import matching_references
from app.services.insights.validation_index import REFERENCE_PATTERN, extract_references

STATISTICS = (
    re.compile(r"평균|\b(?:average|mean)\b", re.I),
    re.compile(r"합계|총합|\b(?:sum|total)\b", re.I),
    re.compile(r"최대|최댓값|\b(?:max|maximum)\b", re.I),
    re.compile(r"최소|최솟값|\b(?:min|minimum)\b", re.I),
)
INCREASE = re.compile(r"증가|늘었|늘어|높아|상승|\bincreas\w*|\brose\b", re.I)
DECREASE = re.compile(r"감소|줄었|줄어|낮아|하락|\bdecreas\w*|\bfell\b", re.I)
QUOTED = re.compile(r'"([^"\n]+)"|“([^”\n]+)”|‘([^’\n]+)’|「([^」\n]+)」')
VALUE = r"-?\d[\d,]*(?:\.\d+)?"
ENDPOINTS = re.compile(
    rf"(?<![\d,.])(?P<old>{VALUE}\s*[A-Za-z가-힣%]*)에서\s*"
    rf"[^.!?;]*?(?<![\d,.])(?P<new>{VALUE}\s*[A-Za-z가-힣%]*?)(?:으로|로)"
)


def grounded_derivation(text, source_text, references, index_changes) -> bool:
    """This checks derivations, not lexical/numeric grounding (checked separately)."""
    text = REFERENCE_PATTERN.sub(" ", text)
    if not NUMBER_PATTERN.search(text):
        return True
    sources = [str(source).strip() for source in source_text]
    if text.strip() in sources:
        return True
    prose = _remove_source_quotes(text, sources)
    for statistic in STATISTICS:
        if statistic.search(prose) and not any(statistic.search(source) for source in sources):
            return False
    rising, falling = bool(INCREASE.search(prose)), bool(DECREASE.search(prose))
    endpoints = list(ENDPOINTS.finditer(prose))
    if not rising and not falling and not endpoints:
        return True
    if rising and falling:
        return False
    changes = [change for change in index_changes if _covered(change, references)]
    changes = [change for change in changes if _consistent_direction(change, rising, falling)]
    if not changes:
        return False
    return all(any(_same_endpoints(match, change) for change in changes) for match in endpoints)


def _remove_source_quotes(text, sources):
    def replace(match):
        quote = next(part for part in match.groups() if part is not None)
        if NUMBER_PATTERN.search(quote) and any(quote in source for source in sources):
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
    return all(
        _decimal(change.get(key)) in _signed_values(match.group(group))
        for group, key in (("old", "earliest_value"), ("new", "latest_value"))
    )


def _signed_values(value):
    candidates = numbers(value)
    return {-item for item in candidates} if value.lstrip().startswith("-") else candidates
