"""Match a computed change to the claim's metric, period and arithmetic."""
from app.services.insights.facts.fact_trends import date_value
from app.services.insights.verification.numeric_validation import numbers, unmatched_numbers


def scoped_changes(text, changes, metric_labels=()):
    from app.services.insights.verification.relation_grounding import label_spans
    from app.services.insights.verification.claim_grounding import REPORT_WORDS
    labels = {str(change.get("metric") or "") for change in changes}
    mentioned = {label for _, _, label in label_spans(text, labels)}
    stated = {label for _, _, label in label_spans(text, metric_labels) if label not in REPORT_WORDS}
    if stated - labels:
        return []
    if mentioned:
        changes = [change for change in changes if change.get("metric") in mentioned]
    elif len(labels - {""}) > 1:
        return []
    return [change for change in changes if _ordered(change)]


def supported_change_numbers(text, changes, source_text=()):
    from app.services.insights.verification.relation_grounding import DATE, label_spans
    from app.services.insights.verification.change_quantities import grounded_change_quantities
    if not grounded_change_quantities(text, changes):
        return False
    from app.services.insights.verification.review_points import grounded_tokens, mask_known_names
    text = mask_known_names(text, grounded_tokens(source_text))
    text = DATE.sub(" ", text)
    labels = {str(change.get("metric") or "") for change in changes}
    for start, end, _ in sorted(label_spans(text, labels), reverse=True):
        text = text[:start] + " " * (end - start) + text[end:]
    candidates = set().union(*(numbers(" ".join(str(change.get(key, "")) for key in (
        "earliest_period", "latest_period", "earliest_value", "latest_value",
        "change", "change_rate_percent",
    ))) for change in changes))
    return not unmatched_numbers(text, candidates)


def same_endpoint_periods(match, change):
    from app.services.insights.verification.relation_grounding import DATE, _same_period
    for group, key, start in (("old", "earliest_period", 0),
                              ("new", "latest_period", match.end("old"))):
        dates = list(DATE.finditer(match.string, start, match.start(group)))
        if dates and change.get(key) and not _same_period(dates[-1].group(), str(change[key])):
            return False
    return True


def _ordered(change):
    first, last = (date_value(str(change.get(key, ""))) for key in (
        "earliest_period", "latest_period",
    ))
    # Legacy numeric changes may lack period labels, but never reverse known dates.
    return not (first and last) or first < last
