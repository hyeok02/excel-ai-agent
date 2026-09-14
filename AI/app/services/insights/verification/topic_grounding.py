"""Only display topics traceable to the cited source, not assembled model phrases."""

from app.services.insights.display.display_quality import is_presentable_label
from app.services.insights.facts.fact_trends import date_value
from app.services.insights.verification.validation_index import extract_references


def grounded_topic(topic, source_text, references, canonical=()):
    if not topic or not is_presentable_label(topic) or date_value(topic) is not None:
        return False
    for item in canonical:
        if topic != item.topic:
            continue
        if required_citations(item, references):
            return True
    phrase = " ".join(topic.split()).casefold()
    return any(phrase in " ".join(source.split()).casefold() for source in source_text)


def required_citations(item, references):
    required = set().union(*(extract_references(ref) for ref in item.evidence))
    return bool(required) and required <= references
