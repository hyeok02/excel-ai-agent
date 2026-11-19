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
    every = build_query_tables(summary)
    tables = [table for table in every if table.complete and table.rows]
    labels = {normalize_reference(column.header_reference) for table in every for column in table.columns}
    labels |= {normalize_reference(cell.reference) for row in index.rows if _year_row(row) for cell in row.cells}
    if not tables:
        return None
    if planner is None:
        from app.agent.query.gpt_calc_planner import LangChainCalcPlanner
        planner = LangChainCalcPlanner.from_environment()
    if planner is None:
        return None
    cells = {normalize_reference(cell.reference): cell for row in index.rows for cell in row.cells}
    note = ""
    for _ in range(2):  # one retry, told what did not run
        plan = await (planner.plan(question, tables, note) if note else planner.plan(question, tables))
        if plan.kind == "table" and plan.table is not None and 0 <= plan.table.table < len(tables):
            from app.agent.query.gpt_calc_tables import run_table
            table = tables[plan.table.table]
            result = await asyncio.to_thread(run_table, table, plan.table)
            if result is not None and (result.groups or plan.table.pick not in {"nth", "top"}):
                return table_answer(question, plan, table, result, _style(table, result, plan.table), cells)
            note = "The table calculation named a column the table does not list, or left no row: name listed columns."
        elif plan.kind == "cells" and plan.cells is not None and plan.cells.items:
            computed = [(item, evaluate(item.expression, cells, labels)) for item in plan.cells.items]
            if all(found is not None for _, found in computed):
                return cells_answer(question, plan, computed)
            bad = [item.expression for item, found in computed if found is None][:5]
            note = (f"These expressions named a header cell or a cell holding no number: {bad}. "
                    "Use the cells of the listed row_values (column letter + row number), never the header_row.")
        else:
            return None
    return None

def _year_row(row):
    """A row of consecutive years (2021, 2022, 2023) names columns even where no table header was read."""
    years = [cell.value for cell in row.cells if isinstance(cell.value, (int, float)) and not isinstance(cell.value, bool)]
    return len(years) >= 3 and all(float(year).is_integer() and 1900 <= year <= 2100 for year in years) \
        and all(later - earlier == 1 for earlier, later in zip(years, years[1:]))


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
