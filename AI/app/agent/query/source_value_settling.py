"""Replace only a generic "could not bind" outcome by an agreed source value.

Deliberate refusals (a semantic mismatch, a missing context, a capability,
formula or join limit) keep their explanation. A clarification stays unless
every source the question can match shows one and the same value.
"""
from app.agent.query.source_series_answers import source_series_answer
from app.agent.query.source_value_answers import source_value_answer

SETTLEABLE = frozenset({
    "clarify_source_scope", "bind_metric_observations", "chronological_trend",
    "tabular_query", "plan_validation", "intent_resolution",
})


def settled_answer(question, sources, answer):
    if answer.status != "insufficient_evidence" or not set(answer.selected_tools) <= SETTLEABLE:
        return answer
    if not answer.selected_tools:
        return answer
    if answer.selected_tools == ["chronological_trend"]:
        return source_series_answer(question, sources.summary, sources.index) or answer
    return source_value_answer(question, sources.summary, sources.index) or answer
