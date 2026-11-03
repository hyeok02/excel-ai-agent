"""Explain category-share captions with their denominator in plain language."""
import re

from app.services.insights.display.source_labels import source_label
from app.services.insights.narratives.narrative_values import subject_particle

_SHARE = re.compile(
    r"^percentage of (?P<base>.+?) with (?P<conditions>.+?) for "
    r"(?P<population>.+?)(?:,\s*(?P<start>(?:19|20|21)\d{2})[-–]"
    r"(?P<end>(?:19|20|21)\d{2}))?$",
    re.I,
)
_BASE_NOUNS = {
    "days": ("날짜", "날"),
    "hours": ("시간", "시간"),
    "records": ("기록", "기록"),
    "cases": ("사례", "사례"),
}


def category_share_subject(caption, metric, header_metrics):
    """Return a readable title, subject and period for a category-share row.

    The rule follows the source's grammar and the actual column headers. It
    does not infer a category, population or denominator from numeric values.
    """
    match = _SHARE.fullmatch(" ".join(str(caption or "").split()))
    if not match:
        return None
    base = match["base"].casefold().strip()
    nouns = _BASE_NOUNS.get(base)
    if not nouns:
        return None
    conditions = match["conditions"]
    spans = _category_spans(conditions, header_metrics)
    metric_span = next((span for name, span in spans if name.casefold() == str(metric).casefold()), None)
    if not metric_span:
        return None
    dimension = conditions[max(span[1] for _, span in spans):].strip(" ,")
    if not dimension:
        return None
    dimension_display = source_label(dimension)
    category_display = source_label(metric, dimension)
    population_display = source_label(match["population"])
    collective, item = nouns
    population_object = "을" if subject_particle(population_display) == "이" else "를"
    dimension_subject = subject_particle(dimension_display)
    subject = (
        f"{population_display}{population_object} 대상으로 집계한 1년 전체 {collective} 중 "
        f"{dimension_display}{dimension_subject} "
        f"'{category_display}'으로 분류된 {item}의 비율"
    )
    title = f"{dimension_display}{dimension_subject} '{category_display}'인 {item}의 비율"
    period = f"{match['start']}~{match['end']}년" if match["start"] else ""
    return title, subject, period


def _category_spans(conditions, header_metrics):
    spans = []
    for value in header_metrics:
        name = " ".join(str(value or "").split())
        if not name:
            continue
        found = re.search(r"(?<![A-Za-z])" + re.escape(name) + r"(?![A-Za-z])", conditions, re.I)
        if found:
            spans.append((name, found.span()))
    return spans
