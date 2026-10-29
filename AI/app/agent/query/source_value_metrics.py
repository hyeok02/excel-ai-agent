"""Metric observations (label rows on a period axis) as consensus candidates.

The same label matching, scope binding and growth-section guards as the
metric answer path are reused; only the final selection differs: values are
answered when every remaining source agrees instead of when exactly one exists.
"""
import re
from datetime import datetime

from app.agent.query.ambiguity_labels import mentioned_sources, source_mentioned
from app.agent.query.ambiguity_metric_scope import bind_explicit_metric_scope
from app.agent.query.ambiguity_metrics import _scalar_observations
from app.agent.query.metric_observation_cells import _numeric, metric_label_matches
from app.agent.query.metric_observation_periods import requested_periods
from app.agent.query.metric_observation_scope import _bind_entity_scope
from app.agent.query.metric_observation_units import observation_unit
from app.agent.query.metric_observations import dated_record_observations, horizontal_observations
from app.agent.query.source_value_terms import FIELD_ONLY, FIELD_TERMS, covers


def metric_values(question, question_terms, index):
    found, rows = matching_observations(question, question_terms, index)
    requests = requested_periods(question)
    if len(requests) > 1:
        return []
    if requests:
        request = requests[0]
        found = [item for item in found if item.period != datetime.min
                 and request.matches(item.period, item.grain, item.scenario)]
        if request.grain is None and request.month is None:
            found = [item for item in found if item.grain == "annual"] or found
    found = [item for item in found if item.scenario not in {"estimate", "budget"}]
    if not requests:
        found = _newest_by_scope(found)
    return [(item, observation_unit(item, rows)) for item in found]


def matching_observations(question, question_terms, index):
    """Numeric observations whose label, scope and context explain every term."""
    _, fields, words = question_terms
    rows = list(index.rows)
    named = mentioned_sources((row.sheet_name for row in rows), question)
    if named:
        rows = [row for row in rows if row.sheet_name in named]
    # Glossary names (e.g. 시가총액 -> market cap) join the label search only.
    probe = " ".join([question, *(alias for field in fields for alias in FIELD_TERMS[field]
                                  if re.fullmatch(r"[a-z][a-z ]+", alias))])
    found = [*_scalar_observations(rows, probe), *horizontal_observations(rows, probe),
             *dated_record_observations(rows, probe)]
    found = [item for item in found if _numeric(item.value.value)]
    exact = [item for item in found if source_mentioned(str(item.label.value), probe)]
    if exact:
        longest = max(len(str(item.label.value).strip()) for item in exact)
        found = [item for item in exact if len(str(item.label.value).strip()) == longest]
    found, scoped = bind_explicit_metric_scope(question, found)
    found = _bind_entity_scope(scoped, found, rows, named) or []
    units = (*fields, *words)
    found = [item for item in found if all(_explained(unit, item, named) for unit in units)]
    return found, rows


def _newest_by_scope(items):
    if any(item.grain == "annual" for item in items):
        items = [item for item in items if item.grain in {None, "annual"}]
    newest = {}
    for item in items:
        key = (item.label.reference, tuple(cell.value for cell in item.entity_cells))
        if key not in newest or item.period > newest[key].period:
            newest[key] = item
    return list(newest.values())


def _explained(unit, item, named):
    texts = [item.label.value]
    if unit not in FIELD_ONLY:
        texts += [*(cell.value for cell in (*item.entity_cells, *item.context_cells)), *named]
    if any(covers(unit, text) for text in texts if text is not None):
        return True
    return unit not in FIELD_TERMS and metric_label_matches(str(item.label.value), unit)
