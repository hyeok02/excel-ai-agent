"""Do not introduce a percentage unit from a matching bare number alone."""
import re
from decimal import Decimal, InvalidOperation

from app.services.insights.numeric_validation import NUMBER_PATTERN, unmatched_numbers
from app.services.insights.reference_matching import matching_references
from app.services.insights.validation_index import REFERENCE_PATTERN, extract_references

PERCENT = r"(?:[%％]|퍼센트|(?<![A-Za-z])percent(?:age)?(?![A-Za-z]))"
PERCENT_MARKER = re.compile(PERCENT, re.I)
PERCENT_VALUE = re.compile(rf"({NUMBER_PATTERN.pattern})\s*{PERCENT}", re.I)


def grounded_units(text, source_text, references, index_changes) -> bool:
    """Supplement lexical/numeric checks with provenance of symbolic percent units."""
    prose = REFERENCE_PATTERN.sub(" ", text)
    if not PERCENT_MARKER.search(prose):
        return True
    if any(PERCENT_MARKER.search(str(source)) for source in source_text):
        return True
    # A computed rate is the only exception to the literal source-unit rule.
    claimed = PERCENT_VALUE.findall(prose)
    if not claimed:
        return False
    rates = {
        rate for change in index_changes
        if _covered(change, references)
        if (rate := _rate(change.get("change_rate_percent"))) is not None
    }
    return bool(rates) and all(not unmatched_numbers(value, rates) for value in claimed)


def _covered(change, references):
    if not isinstance(change, dict):
        return False
    evidence = change.get("evidence")
    if not isinstance(evidence, list) or not evidence:
        return False
    required = [extract_references(str(item)) for item in evidence]
    if any(not parsed for parsed in required):
        return False
    return all(
        any(matching_references(reference, {item}) for reference in references)
        for item in set().union(*required)
    )


def _rate(value):
    if isinstance(value, bool) or value is None:
        return None
    try:
        rate = Decimal(str(value))
        return abs(rate) if rate.is_finite() else None
    except InvalidOperation:
        return None
