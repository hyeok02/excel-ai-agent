"""Expose competing metric periods/units instead of a generic refusal."""
from datetime import datetime

from app.agent.query.ambiguity_metric_scope import bind_explicit_metric_scope
from app.agent.query.ambiguity_candidates import AmbiguousCandidate
from app.agent.query.ambiguity_labels import source_mentioned
from app.agent.query.metric_observation_cells import MetricObservation, _column, _human_label, _numeric
from app.agent.query.metric_observation_periods import LATEST, requested_periods
from app.agent.query.metric_observation_render import _metric_identity, _period_label
from app.agent.query.metric_observation_scope import _bind_entity_scope
from app.agent.query.metric_observation_units import observation_unit
from app.agent.query.metric_observations import horizontal_observations, dated_record_observations, metric_label_matches
from app.agent.query.metric_scalar_answers import _BLOCKED


def metric_candidates(question, index):
    rows = list(index.rows)
    named = {row.sheet_name for row in rows if source_mentioned(row.sheet_name, question)}
    if named:
        rows = [row for row in rows if row.sheet_name in named]
    requests = requested_periods(question)
    latest = bool(LATEST.search(question))
    if not requests and _BLOCKED.search(question):
        return []
    # Without a requested period, a distinctly labelled snapshot is the
    # natural scalar target; history axes must not obscure that source value.
    observations = _scalar_observations(rows, question) if not (requests or latest) else []
    if not observations:
        observations = horizontal_observations(rows, question)
    if latest:
        observations.extend(dated_record_observations(rows, question))
    if not observations:
        return []
    exact = [item for item in observations if source_mentioned(str(item.label.value), question)]
    if exact:
        longest = max(len(str(item.label.value).strip()) for item in exact)
        observations = [item for item in exact if len(str(item.label.value).strip()) == longest]
    observations, scope_question = bind_explicit_metric_scope(question, observations)
    observations = _bind_entity_scope(scope_question, observations, rows, named) or []
    if len({_metric_identity(item.label.value) for item in observations}) != 1:
        return []
    groups = []
    for request in requests:
        selected = [item for item in observations if request.matches(item.period, item.grain, item.scenario)]
        if request.grain is None and request.month is None:
            selected = [item for item in selected if item.grain == "annual"] or selected
        if request.scenario is None:
            selected = [item for item in selected if item.scenario == "actual"] or selected
        groups.append(selected)
    if latest and not requests:
        actual = [item for item in observations if item.scenario not in {"estimate", "budget"}]
        if actual:
            # "Latest" chooses a date within a source population, not which
            # company/report block wins merely because it has a newer date.
            scopes = {(item.label.reference, tuple(cell.value for cell in item.entity_cells))
                      for item in actual}
            if len(scopes) > 1:
                newest_by_scope = {}
                for item in actual:
                    key = (item.label.reference, tuple(cell.value for cell in item.entity_cells))
                    if key not in newest_by_scope or item.period > newest_by_scope[key].period:
                        newest_by_scope[key] = item
                return [_candidate(item, rows) for item in newest_by_scope.values()]
            newest = max(item.period for item in actual)
            groups.append([item for item in actual if item.period == newest])
    elif not requests:
        groups.append(observations)
    for group in groups:
        identities = {(item.period, item.grain, item.scenario, item.value.value,
                       observation_unit(item, rows).identity) for item in group}
        if len(identities) > 1:
            return [_candidate(item, rows) for item in group]
    return []


def _scalar_observations(rows, question):
    observations = []
    for row in rows:
        labels = [cell for cell in row.cells if _human_label(cell)]
        for label in labels:
            if not metric_label_matches(str(label.value), question):
                continue
            left = _column(label)
            right = min((_column(cell) for cell in labels if _column(cell) > left), default=16_385)
            numbers = [cell for cell in row.cells if left < _column(cell) < right and _numeric(cell.value)]
            if len(numbers) == 1:
                observations.append(MetricObservation(label, numbers[0], datetime.min, label, None, None, ()))
    return observations


def _candidate(item, rows):
    unit = observation_unit(item, rows)
    dated = item.period != datetime.min
    period = _period_label(item) if dated else "기준일 없음"
    entity = " / ".join(str(cell.value) for cell in item.entity_cells)
    unit_text = (f"단위: {unit.suffix}" if unit.suffix else
                 f"표시 형식: {item.value.number_format}" if item.value.number_format != "General"
                 else "단위 미확인")
    details = "; ".join(filter(None, [entity, period, unit_text]))
    qualified = f"'{item.value.sheet_name}'!{item.value.address}"
    # An exact cell address is the final unambiguous fallback even when a sheet
    # contains repeated same-name company blocks or conflicting unit captions.
    followup = f"{qualified}의 {item.label.value} 값을 {period if dated else ''} 알려줘"
    cells = tuple(dict.fromkeys((item.label, item.value, item.period_cell, *item.context_cells,
                                *item.entity_cells, *unit.references)))
    return AmbiguousCandidate(str(item.label.value), qualified, details, followup, cells)
