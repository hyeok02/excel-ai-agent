"""Resolve only an omitted source-language label; keep all numbers deterministic."""
from dataclasses import replace
import re

from app.agent.query.tabular_source_alias import alias_lookup_request, source_label_alias_answer
from app.agent.query.tabular_source_alias_resolver import LangChainSourceLabelResolver
from app.agent.query.quota_errors import raise_for_quota_exhaustion


async def resolved_source_label_alias_answer(question, summary, data_index, intent, clarification, resolver=None):
    direct = source_label_alias_answer(question, summary, data_index, intent, clarification)
    if direct is not None:
        return direct
    request = alias_lookup_request(question, summary, intent, clarification)
    if request is None:
        return None
    subject, _, table, plan = request
    condition = plan.filters[0]
    # Never replace an explicit source label, contradictory model-selected
    # English label, missing identity, or multiple filters with a guessed name.
    if condition.value.strip() != subject:
        return None
    values = sorted({row.values[condition.column_id] for row in table.rows
                     if isinstance(row.values[condition.column_id], str)
                     and re.fullmatch(r"[A-Za-z][A-Za-z .&'()-]{1,79}", row.values[condition.column_id])})
    if not values or len(values) > 250 or sum(map(len, values)) > 16000:
        return None
    resolver = resolver or LangChainSourceLabelResolver.from_environment()
    if resolver is None:
        return None
    field = next(column.header for column in table.columns if column.id == condition.column_id)
    try:
        result = await resolver.resolve(subject, field, values)
    except Exception as exception:
        raise_for_quota_exhaustion(exception)
        return None
    if (result.status != "resolved" or type(result.candidate_id) is not int
            or not 0 <= result.candidate_id < len(values)):
        return None
    selected = values[result.candidate_id]
    updated = plan.model_copy(update={"filters": [condition.model_copy(update={"value": selected})]})
    return source_label_alias_answer(question, summary, data_index,
                                     replace(intent, tabular_query=updated), clarification)
