"""Short topic labels copied from cited source headings, never inferred from a filename."""
import re

from app.services.insights.display.glossary import readable
from app.services.insights.display.display_quality import is_presentable_label
from app.services.insights.facts.fact_trends import date_value


def source_topic(value):
    """Keep only a bounded textual source label suitable for a section heading."""
    text = " ".join(str(value or "").split()).strip(" \"'.,:;")
    if (not 2 <= len(text) <= 60 or not is_presentable_label(text)
            or text.startswith("=") or date_value(text)
            or re.search(r"https?://|\\\\", text, re.I)
            or not re.search(r"[A-Za-z가-힣]", text)):
        return None
    displayed = readable(text)
    return displayed if len(displayed) <= 70 else text


def scoped_source_topic(metric, metric_cell, scope, scope_cell):
    topic = source_topic(metric) if metric_cell else None
    scope_topic = source_topic(scope) if scope_cell else None
    return f"{scope_topic}의 {topic}" if scope_topic and topic else topic
