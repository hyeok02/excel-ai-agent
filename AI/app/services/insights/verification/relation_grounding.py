"""Bind every stated scalar to its cited field and row qualifiers."""
import re
from functools import lru_cache

from app.services.insights.verification.numeric_validation import (
    NUMBER_PATTERN, _number_tokens, _matches_candidate, numbers,
)
from app.services.insights.verification.reference_matching import matching_references
from app.services.insights.verification.source_scalars import negative

CLAUSES = re.compile(r"[;\n]|(?<!\d)[.!?]|[.!?](?!\d)|,(?!\d)|(?<=했고)\s+|(?<=했으며)\s+")
DATE = re.compile(r"\d{4}(?:[-/.]\d{1,2}(?:[-/.]\d{1,2})?|년(?:\s*\d{1,2}월(?:\s*\d{1,2}일)?)?)")
OWNER_SUFFIX = re.compile(r"의\s+(?:주요\s*)?(?:수치|지표|항목|내용)")
LABEL_TEXT = re.compile(r"[A-Za-z가-힣]")
ANCHOR_PART = re.compile(r"[\x00-\x7f가-힣]+")
# These four characters also match ASCII letters under Python's Unicode re.I.
# Only this conservative alphabet is prefiltered; the original regex below
# remains authoritative for Unicode, whitespace, and left-boundary semantics.
ASCII_CASE_EQUIVALENTS = str.maketrans({"İ": "i", "ı": "i", "ſ": "s", "K": "k"})


@lru_cache(maxsize=8192)
def _label_anchor(label):
    if not label or not LABEL_TEXT.search(label):
        return None
    parts = [part.lower() for word in str(label).split()
             for part in ANCHOR_PART.findall(word)]
    return max(parts, key=len, default="")


@lru_cache(maxsize=8192)
def _label_pattern(label):
    pattern = r"\s*".join(re.escape(word) for word in str(label).split())
    return re.compile(r"(?<![A-Za-z가-힣])" + pattern, re.I)


def label_spans(text, labels):
    spans = []
    folded_text = text.translate(ASCII_CASE_EQUIVALENTS).lower()
    for label in set(labels):
        anchor = _label_anchor(label)
        if anchor is None or anchor not in folded_text:
            continue
        for match in _label_pattern(label).finditer(text):
            spans.append((match.start(), match.end(), label))
    return [span for span in spans if not any(
        other != span and other[0] <= span[0] and other[1] >= span[1]
        and other[1] - other[0] > span[1] - span[0] for other in spans
    )]


def grounded_relations(text, references, observations):
    observed = [item for item in observations if all(
        any(matching_references(ref, {required}) for ref in references)
        for required in item.references
    )]
    if not observed:
        return True  # Formula/computed-only evidence has its separate checks.
    labels = {label for item in observed for label in (*item.labels, *item.qualifiers)}
    for clause in CLAUSES.split(text):
        from app.services.insights.verification.change_quantities import derived_spans
        derived, _ = derived_spans(clause)
        spans = sorted(label_spans(clause, labels))
        dates = list(DATE.finditer(clause))
        previous = 0
        for match in NUMBER_PATTERN.finditer(clause):
            if any(start <= match.start() < end for start, end in derived):
                continue
            if any(start <= match.start() < end for start, end, _ in spans):
                continue
            if any(date.start() <= match.start() < date.end() for date in dates):
                continue
            before = [span for span in spans if span[1] <= match.start()]
            current = [span for span in before if span[0] >= previous]
            relevant = current or before[-1:]
            candidates = [item for item in observed if all(
                label in (*item.labels, *item.qualifiers) for _, _, label in relevant
            )]
            if not relevant and len({(item.labels, item.value) for item in observed}) > 1:
                return False
            earlier_dates = [date for date in dates if date.end() <= match.start()]
            if earlier_dates:
                candidates = [item for item in candidates if _same_period(earlier_dates[-1].group(), item.period)]
            if not any(_matches(match, clause, item.value) for item in candidates):
                return False
            previous = match.end()
    return True


def grounded_metric_owner(text, references, observations):
    """A metric name cannot become the owner of unrelated metric values.

    Check this even for source-generated/canonical prose. A region caption can
    be a heuristic copy of the first metric label, so matching canonical text
    is not independent evidence for that relationship.
    """
    # Most fields contain no ownership claim. Do not scan every source label
    # for those fields; this guard is a necessary part of the exact old rule.
    if not OWNER_SUFFIX.search(text):
        return True
    labels = {label for item in observations for label in item.labels}
    all_spans = label_spans(text, labels)
    owners = [(end, label) for _, end, label in all_spans
              if OWNER_SUFFIX.match(text, end)]
    if not owners:
        return True
    cited = [item for item in observations if all(
        any(matching_references(ref, {required}) for ref in references)
        for required in item.references
    )]
    for end, owner in owners:
        for match in NUMBER_PATTERN.finditer(text, end):
            if any(start <= match.start() < stop for start, stop, _ in all_spans):
                continue
            candidates = [item for item in cited if _matches(match, text, item.value)]
            if candidates and not any(owner in (*item.labels, *item.qualifiers)
                                      for item in candidates):
                return False
    return True


def _matches(match, text, source):
    if negative(source) != match.group().startswith("-"):
        return False
    # Reuse the existing magnitude/percentage rounding rules after checking sign.
    return _matches_candidate(_number_tokens(text[match.start():])[0], numbers(source))


def _same_period(text, period):
    if not period:
        return False
    stated = [int(value) for value in re.findall(r"\d+", text)]
    actual = [int(value) for value in re.findall(r"\d+", period)[:3]]
    return actual[:len(stated)] == stated
