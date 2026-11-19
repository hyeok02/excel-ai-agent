"""Whether every number in GPT's own answer is a source value it saw, or one step of arithmetic on two.

A draft the validator could not tie to cited cells is shown only when its numbers are recomputed
here: 66 next to 849 and 783 is 849-783, 84.61% next to 58,620,101 and 69,281,437 is their ratio.
A number nothing produces (999 beside a cell holding 120) keeps the draft hidden.
"""
import re
from bisect import bisect_left
from itertools import permutations

from app.agent.query.references import normalize_reference

MAX_VALUES = 400
_NUMBER = re.compile(r"(?<![A-Za-z가-힣\d.])-?\d[\d,]*(?:\.\d+)?")
_UNIT = re.compile(r"\s*(?:년|월|일|위|번째|개월|분기|시|분|차)")


def source_values(execution):
    values = []
    for step in getattr(execution, "steps", []) or []:
        for item in (step.result.evidence if step.result else []):
            if isinstance(item.value, (int, float)) and not isinstance(item.value, bool):
                values.append(float(item.value))
    return list(dict.fromkeys(values))[:MAX_VALUES]


def source_references(execution):
    return {normalize_reference(item.reference) for step in getattr(execution, "steps", []) or []
            for item in (step.result.evidence if step.result else []) if item.reference}


def cites_only_seen_cells(evidence, references):
    """A draft citing a cell it was never shown (Z999) is not shown, whatever its numbers."""
    for reference in evidence:
        sheet, _, cells = str(reference).rpartition("!")
        first = f"{sheet}!{cells.split(':')[0]}" if sheet else reference
        if normalize_reference(first) not in references and normalize_reference(reference) not in references:
            return False
    return True


def _candidates(values):
    yield from values
    for a, b in permutations(values, 2):
        yield a - b
        yield a + b
        if b:
            yield a / b
            yield a / b * 100
            yield (a - b) / b * 100


def numbers_hold(text, values):
    """True when each number written in ``text`` is a value or one operation on two values."""
    found = []
    for match in _NUMBER.finditer(text):
        rest = text[match.end():]
        if _UNIT.match(rest):
            continue  # a date, an ordinal or a period, not a figure
        raw = match.group().replace(",", "")
        value = float(raw)
        if value.is_integer() and 0 <= value <= 10:
            continue  # a count of listed items or a list number
        decimals = len(raw.partition(".")[2])
        found.append((abs(value), 0.5 * 10 ** -decimals + 1e-9 * abs(value)))
    if not found:
        return True
    pool = sorted(abs(value) for value in _candidates(values))
    return all(_near(pool, value, tolerance) for value, tolerance in found)


def _near(pool, value, tolerance):
    at = bisect_left(pool, value - tolerance)
    return at < len(pool) and pool[at] <= value + tolerance
