"""Use source labels and bounded measure-family aliases for time series."""
import re

from app.agent.query.metric_observation_cells import (
    _DATE_HEADER, _korean_metric_in_question, _normal, metric_label_matches,
)
from app.agent.query.search_terms import SEMANTIC_ALIASES
from app.services.insights.display.glossary import translate


def trend_label_spellings(label):
    return tuple(dict.fromkeys(value for value in (str(label), translate(label)) if value))


def trend_metric_label_matches(label, question):
    if _DATE_HEADER.search(str(label)):
        return False
    translated = translate(label)
    return (metric_label_matches(label, question)
            or bool(translated and _korean_metric_in_question(translated, question))
            or _measure_family_matches(label, question))


def _measure_family_matches(label, question):
    """Match a Korean rate-family term to an embedded English measure word.

    A source label such as ``Current Asthma Prevalence`` is more specific than
    the user's ``천식 유병률``.  Requiring a Korean ``률/율`` concept and a
    whole English token permits safe candidate discovery while leaving the
    final choice to source clarification when several measures match.
    """
    normalized = _normal(label)
    for concept, aliases in SEMANTIC_ALIASES.items():
        if not concept.endswith(("률", "율")) or not _korean_metric_in_question(concept, question):
            continue
        for alias in aliases:
            token = _normal(alias)
            if token and " " not in token and re.search(r"(?<![a-z0-9])" + re.escape(token) + r"(?![a-z0-9])", normalized):
                return True
    return False


def trend_column_matches(column, question):
    from app.agent.query.metric_semantics import column_metric_conflict
    return trend_metric_label_matches(column.header, question) and not column_metric_conflict(column, question)
