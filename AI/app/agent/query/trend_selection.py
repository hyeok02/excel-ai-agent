"""Select a unique complete series; identical copies are not extra populations."""
from dataclasses import replace
import re

from app.agent.query.ambiguity_labels import mentioned_sources
from app.agent.query.metric_observation_render import _metric_identity
from app.agent.query.metric_observation_cells import _normal
from app.agent.query.trend_labels import trend_label_spellings
from app.agent.query.metric_observation_units import observation_unit
from app.agent.query.tabular_request_scope import explicit_ranges, _inside


def scoped_trend_candidates(question, candidates, summary):
    named = mentioned_sources((sheet.name for sheet in summary.sheets), question)
    if named:
        candidates = [item for item in candidates if item.table_id.rpartition("!")[0] in named]
    ranges = explicit_ranges(question)
    if ranges:
        candidates = [item for item in candidates if item.observations and all(
            any(sheet == point.value.sheet_name and _inside(point.value.address, reference)
                and _inside(point.period_cell.address, reference) for sheet, reference in ranges)
            for point in item.observations)]
    # A named metric plus a generic descriptor ("Services 인원") identifies the
    # named metric, not every headcount column in the workbook. Coordinated
    # requests still keep all candidates and cannot drop the other measure.
    if not re.search(r"\band\b|및|하고|[가-힣a-z0-9)](?:와|과)\s", question, re.I):
        exact = [item for item in candidates if any(
            _normal(label) and re.search(
                r"(?<!\w)" + re.escape(_normal(label)) + r"(?![a-z0-9])", _normal(question))
            for cell in ([item.observations[0].label] if item.observations else item.context[:1])
            for label in trend_label_spellings(cell.value))]
        if exact:
            candidates = exact
    return candidates, named


def prepare_trend_candidate(candidate, rows):
    if candidate.error:
        return candidate, ()
    by_date = {}
    identities = set()
    for point in candidate.observations:
        unit = observation_unit(point, rows)
        if unit.identity[0:1] == ("conflicting_units",):
            return replace(candidate, error="conflicting_units"), ()
        identity = (point.grain, point.scenario, unit.identity)
        identities.add(identity)
        prior = by_date.get(point.period)
        if prior is not None and (prior.value.value != point.value.value or
                                  observation_unit(prior, rows).identity != unit.identity):
            return replace(candidate, error="duplicate_period"), ()
        by_date.setdefault(point.period, point)
    if len(identities) != 1:
        return replace(candidate, error="mixed_series_context"), ()
    if len(by_date) < 2:
        return replace(candidate, error="insufficient_periods"), ()
    points = tuple(by_date[key] for key in sorted(by_date))
    return replace(candidate, observations=points), tuple(observation_unit(item, rows) for item in points)


def distinct_trend_candidates(prepared, *, preserve_labels=False):
    distinct = []
    for candidate, units in prepared:
        # Entity/currency/scenario captions are part of identity, not just values.
        entities = tuple(sorted({str(cell.value) for point in candidate.observations
                                 for cell in point.entity_cells}))
        label = str(candidate.observations[0].label.value)
        identity = label.casefold().strip() if preserve_labels else _metric_identity(label)
        key = (identity, entities, tuple(
            (point.period, point.value.value, point.grain, point.scenario, unit.identity)
            for point, unit in zip(candidate.observations, units)))
        if not any(existing[0] == key for existing in distinct):
            distinct.append((key, candidate, units))
    return [(candidate, units) for _, candidate, units in distinct]
