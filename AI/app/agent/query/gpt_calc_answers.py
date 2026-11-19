"""The last resort for a question nothing answered: GPT chooses a calculation, code runs it.

Before, such a question ended in "현재 원본 근거로 확인 가능한 답변이 없습니다" although GPT had
seen only 30 searched rows and was not allowed to calculate. Now GPT names the calculation over the
whole table (or over cells it cites), code computes it from the source, and the answer states the
calculation so it can be checked. If no calculation runs, GPT's own unverified draft is shown, marked.
Questions answered before, and questions that ask back with options, never reach this.
"""
import asyncio
from contextvars import ContextVar

from app.agent.query.gpt_calc_answer_text import cells_answer, table_answer, unverified_draft
from app.agent.query.gpt_calc_cells import evaluate
from app.agent.query.gpt_calc_draft_check import source_references, source_values
from app.agent.query.models import QuestionAnswerStatus
from app.agent.query.quota_errors import raise_for_quota_exhaustion
from app.agent.query.references import normalize_reference
from app.agent.query.tabular_catalog import build_query_tables

_DRAFTS: ContextVar[list | None] = ContextVar("generated_drafts", default=None)


def start_collecting_drafts():
    return _DRAFTS.set([])


def stop_collecting_drafts(token):
    _DRAFTS.reset(token)


def keep_draft(draft, execution):
    if (drafts := _DRAFTS.get()) is not None:
        drafts.append((draft, source_values(execution), source_references(execution)))


def needs_fallback(answer):
    return (answer.status == QuestionAnswerStatus.INSUFFICIENT_EVIDENCE and not answer.clarification_options
            and "clarify_source_scope" not in answer.selected_tools)


async def fallback_answer(question, summary, index, answer, planner=None):
    drafts = list(_DRAFTS.get() or [])
    try:
        computed = await _computed(question, summary, index, planner)
    except Exception as exception:
        raise_for_quota_exhaustion(exception)
        computed = None
    return computed or (unverified_draft(question, answer, *drafts[-1]) if drafts else None) or answer


async def _computed(question, summary, index, planner):
    if summary is None or index is None:
        return None
    tables = [table for table in build_query_tables(summary) if table.complete and table.rows]
    if not tables:
        return None
    if planner is None:
        from app.agent.query.gpt_calc_planner import LangChainCalcPlanner
        planner = LangChainCalcPlanner.from_environment()
    if planner is None:
        return None
    plan = await planner.plan(question, tables)
    cells = {normalize_reference(cell.reference): cell for row in index.rows for cell in row.cells}
    if plan.kind == "table" and plan.table is not None and 0 <= plan.table.table < len(tables):
        from app.agent.query.gpt_calc_tables import run_table
        table = tables[plan.table.table]
        result = await asyncio.to_thread(run_table, table, plan.table)
        if result is None or not result.groups and plan.table.pick in {"nth", "top"}:
            return None
        style = _style(table, result, plan.table)
        return table_answer(question, plan, table, result, style, cells)
    if plan.kind == "cells" and plan.cells is not None and plan.cells.items:
        computed = [(item, evaluate(item.expression, cells)) for item in plan.cells.items]
        if any(found is None for _, found in computed):
            return None  # a reference that is not a number cell: nothing is guessed
        return cells_answer(question, plan, computed)
    return None


def _style(table, result, calc):
    if calc.aggregate in {"count", "count_distinct"} or not calc.measure:
        return "#,##0"
    measure = result.columns[-1]
    formats = [row.number_formats.get(measure.id) for row in table.rows if row.number_formats.get(measure.id)]
    return formats[0] if formats else "General"



async def with_calculation_fallback(question, sources, produce):
    """``produce()``'s answer, or, when it answers nothing, the GPT-chosen calculation's."""
    token = start_collecting_drafts()
    try:
        answer = await produce()
        if needs_fallback(answer):
            answer = await fallback_answer(answer.resolved_question or question, sources.summary, sources.index, answer)
    finally:
        stop_collecting_drafts(token)
    return answer
