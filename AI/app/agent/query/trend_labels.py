"""Use existing display translations only for whole, actual source labels."""
from app.agent.query.metric_observation_cells import (
    _DATE_HEADER, _korean_metric_in_question, metric_label_matches,
)
from app.services.insights.display.glossary import translate


def trend_label_spellings(label):
    return tuple(dict.fromkeys(value for value in (str(label), translate(label)) if value))


def trend_metric_label_matches(label, question):
    if _DATE_HEADER.search(str(label)):
        return False
    translated = translate(label)
    return metric_label_matches(label, question) or bool(
        translated and _korean_metric_in_question(translated, question))


def trend_column_matches(column, question):
    from app.agent.query.metric_semantics import column_metric_conflict
    return trend_metric_label_matches(column.header, question) and not column_metric_conflict(column, question)
