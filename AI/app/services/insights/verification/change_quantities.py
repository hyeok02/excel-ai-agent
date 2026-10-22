"""Distinguish observed endpoints from a stated change amount or rate."""
import re

from app.services.insights.verification.numeric_validation import (
    _number_tokens, _matches_candidate, numbers,
)

QUANTITY = re.compile(
    r"(?P<amount>-?\d[\d,]*(?:\.\d+)?)\s*(?P<unit>[A-Za-z가-힣%]*?)"
    r"(?:\s*\(\s*(?P<rate>-?\d[\d,]*(?:\.\d+)?)\s*%\s*\))?\s*"
    r"(?:증가|감소|늘었|늘어|높아|상승|줄었|줄어|낮아|하락|increas|decreas)", re.I,
)
GRAMMAR = re.compile(r"이고|이며|입니다|에서|으로|보다|대비|까지|부터|^로$")


def derived_spans(text):
    from app.services.insights.verification.derived_claim_grounding import ENDPOINTS
    endpoints = list(ENDPOINTS.finditer(text))
    spans = [match.span(group) for match in endpoints for group in ("old", "new")]
    quantities = [match for match in QUANTITY.finditer(text)
                  if not GRAMMAR.search(match.group("unit"))
                  and not any(start <= match.start("amount") < end for start, end in spans)]
    spans.extend(match.span(group) for match in quantities for group in ("amount", "rate")
                 if match.group(group) is not None)
    return spans, quantities


def grounded_change_quantities(text, changes):
    _, quantities = derived_spans(text)
    for match in quantities:
        for group in ("amount", "rate"):
            value = match.group(group)
            if value is None:
                continue
            if value.startswith("-"):
                return False
            percent = group == "rate" or "%" in match.group("unit")
            key = "change_rate_percent" if percent else "change"
            candidates = set().union(*(numbers(str(change.get(key, ""))) for change in changes))
            # The rate field already uses percent units; don't divide it by 100 again.
            suffix = "" if percent else match.group("unit")
            if not _matches_candidate(_number_tokens(value + suffix)[0], candidates):
                return False
    return True
