"""A lookup whose question word fits several rows shows them all rather than one of them."""
import asyncio
from dataclasses import replace

from app.agent.query.models import QuestionVerificationLevel
from app.agent.query.tabular_execution import execute_tabular_query
from app.agent.query.tabular_member_rows import member_ranking
from app.agent.query.tabular_population_context import MIXED_ROLES, OVERLAPPING_TOTALS


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


async def run_checked(plan, summary, data_index, rewritten, intent, question):
    """Run the read plan; a ranking refused only for ranking groups with their members ranks the members."""
    answer = await asyncio.to_thread(execute_tabular_query, plan, summary, data_index, rewritten, intent)
    if answer is not None and answer.answer in {MIXED_ROLES, OVERLAPPING_TOTALS}:
        return await member_ranking(plan, summary, data_index, question) or answer
    return answer


def ranked_members(answer):
    return "member_rows" in answer.selected_tools
