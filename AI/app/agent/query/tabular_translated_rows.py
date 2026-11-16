"""A lookup whose question word fits several rows shows them all rather than one of them."""
import asyncio
from dataclasses import replace

from app.agent.query.models import QuestionVerificationLevel
from app.agent.query.tabular_execution import execute_tabular_query


async def every_row(plan, summary, data_index, question, intent, conditions, found, totals):
    """A lookup whose word fits several rows ("천식 유병률") drops that condition and shows them all,
    if the ordinary checks pass it as they would a plan without it; an aggregation never widens."""
    unnamed = [condition for condition, named, total in zip(conditions, found, totals) if named == [] and not total]
    if plan.operation != "lookup" or not unnamed or plan.filter_expression is not None:
        return None
    wider = plan.model_copy(update={"filters": [item for item in plan.filters if item not in unnamed]})
    answer = await asyncio.to_thread(execute_tabular_query, wider, summary, data_index, question,
                                     replace(intent, tabular_query=wider))
    return answer if answer and answer.verification.level == QuestionVerificationLevel.REQUEST_CHECKED else None
