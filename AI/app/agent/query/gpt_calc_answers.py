"""The last resort for a question nothing answered: GPT chooses a calculation, code runs it.
GPT names the calculation over a whole table (or cells it cites), code computes it from the source and states
it; else GPT's draft is shown, marked. Answered questions and needed ask-backs never reach this (gpt_calc_choices).
"""
import asyncio
from contextvars import ContextVar


from app.agent.query.gpt_calc_answer_text import cells_answer, table_answer, unverified_draft
from app.agent.query.gpt_calc_cells import evaluate
from app.agent.query.gpt_calc_draft_check import source_references, source_values
from app.agent.query.gpt_calc_checks import (
    fitting_table, listed_cells, plan_problem, unlisted_note, unused_values, with_cell_values)
from app.agent.query.group_rows import group_rows, section_rows
from app.agent.query.models import QuestionAnswerStatus
from app.agent.query.quota_errors import raise_for_quota_exhaustion
from app.agent.query.references import normalize_reference
from app.agent.query.tabular_catalog import build_query_tables
from app.agent.query.gpt_calc_choices import unneeded_choice
from app.agent.query.gpt_calc_full_rows import completed_tables, scoped_tables
from app.agent.query.gpt_calc_scope_checks import in_scope, year_problem
from app.agent.query.gpt_calc_stacked import statement_and_period_tables
from app.agent.query.tabular_explicit_scope import explicit_ranges

_DRAFTS: ContextVar[list | None] = ContextVar("generated_drafts", default=None)


def start_collecting_drafts():
    return _DRAFTS.set([])


def stop_collecting_drafts(token):
    _DRAFTS.reset(token)


def keep_draft(draft, execution):
    if (drafts := _DRAFTS.get()) is not None:
        drafts.append((draft, source_values(execution), source_references(execution)))


# Answers GPT wrote from ~30 searched rows: totals over a whole table need every row, so a calculation is preferred.
_UNLISTED = "The table calculation named a column the table does not list, or left no row: name listed columns."
_SEARCHED = {"search_workbook_data", "inspect_semantic_structure", "recover_formula_values"}


def needs_fallback(answer, summary=None):
    if answer.clarification_options or "clarify_source_scope" in answer.selected_tools:
        return unneeded_choice(answer, summary)  # asking back is an answer, unless the question settles it
    return answer.status == QuestionAnswerStatus.INSUFFICIENT_EVIDENCE or bool(answer.selected_tools) and set(
        answer.selected_tools) <= _SEARCHED and answer.verification.level != "request_checked" or (
        "column_summaries" in answer.verification.checks)  # each column summarized apart: GPT may combine them


async def fallback_answer(question, summary, index, answer, planner=None):
    drafts = list(_DRAFTS.get() or [])
    try:
        computed = await _computed(question, summary, index, planner)
    except Exception as exception:
        raise_for_quota_exhaustion(exception)
        computed = None
    unanswered = answer.status == QuestionAnswerStatus.INSUFFICIENT_EVIDENCE
    if computed is not None and not unanswered and "calculation" not in computed.verification.checks:
        computed = None  # a list of names only does not replace an answer that states figures
    return computed or (unverified_draft(question, answer, *drafts[-1]) if drafts and unanswered else None) or answer


async def _computed(question, summary, index, planner):
    if summary is None or index is None:
        return None
    every = build_query_tables(summary)
    tables = completed_tables(every, index)  # a list larger than the summary's sample is read whole
    if scopes := explicit_ranges(question):  # "Sales!A1:D3 범위의 …": only the rows and columns of that range
        tables = scoped_tables(tables, scopes)
    labels = {normalize_reference(column.header_reference) for table in every for column in table.columns}
    labels |= {normalize_reference(cell.reference) for row in index.rows if _year_row(row) for cell in row.cells}
    if not (tables := statement_and_period_tables(tables, index)):  # row names; month sheets as one table
        return None
    from app.agent.query.gpt_calc_planner import LangChainCalcPlanner
    if (planner := planner or LangChainCalcPlanner.from_environment()) is None:
        return None
    cells = {normalize_reference(cell.reference): cell for row in index.rows for cell in row.cells}
    cells = in_scope(cells, scopes) if scopes else cells  # a formula plan reads only the range named, as a table plan
    listed = listed_cells(tables, cells)  # kind=cells may cite only the rows GPT was shown
    headings = {table.id: {**section_rows(table), **group_rows(table, summary)} for table in tables}
    note = ""
    for attempt in range(2):  # one retry, told what did not run; the retried plan is checked the same way
        try:
            plan = await planner.plan(question, tables, note, headings)
        except Exception as exception:  # a plan cut off at the length limit is asked for once more, shorter
            raise_for_quota_exhaustion(exception)
            note = "The previous plan was cut off at the length limit: write a short plan with few filters."
            continue
        table = fitting_table(tables, plan.table.table, plan.table) if plan.kind == "table" and plan.table else None
        if plan.kind == "table" and plan.table is not None and table is not None:
            from app.agent.query.gpt_calc_tables import run_table
            if not attempt and (problem := plan_problem(question, table, plan.table, headings.get(table.id))):
                note = problem
                continue
            if attempt and (unused_values(question, table, plan.table) or year_problem(question, table, plan.table)):
                return None
            plan = plan.model_copy(update={"table": with_cell_values(plan.table, cells, question)})  # "> [Table!B66]"
            result = await asyncio.to_thread(run_table, table, plan.table, headings.get(table.id))
            echo = plan.table.aggregate == "count" and len(result.groups) == 1 and result.groups[0][1] == 1 \
                and result.groups[0][0] != "전체" if result is not None else False  # one name back, no figure
            if result is not None and not echo and (result.groups or plan.table.pick not in {"nth", "top"}):
                return table_answer(question, plan, table, result, _style(table, result, plan.table), cells)
            note = _UNLISTED
        elif plan.kind == "cells" and plan.cells is not None and plan.cells.items:
            computed = [(item, evaluate(item.expression, listed, labels, cells)) for item in plan.cells.items]
            if all(found is not None for _, found in computed):
                return cells_answer(question, plan, computed)
            bad = [item.expression for item, found in computed if found is None][:5]
            note = (f"These expressions named a header cell or a cell holding no number: {bad}. "
                    "Use the cells of the listed row_values (column letter + row number), never the header_row; a table "
                    "listed without row_values is read with kind=table and filters (a total row by its own label).")
        elif plan.kind == "table" and plan.table is not None:  # a column no table lists: told, asked once more
            note = unlisted_note(tables, plan.table.table, plan.table) or _UNLISTED
        else:
            return None
    return None

def _year_row(row):
    """A row of consecutive years (2021, 2022, 2023) names columns even where no table header was read."""
    years = [cell.value for cell in row.cells if isinstance(cell.value, (int, float)) and not isinstance(cell.value, bool)]
    return len(years) >= 3 and all(float(year).is_integer() and 1900 <= year <= 2100 for year in years) \
        and all(later - earlier == 1 for earlier, later in zip(years, years[1:]))


def _style(table, result, calc):
    if calc.aggregate == "ratio" or calc.versus_previous == "rate":  # 전월 대비 증가율: 59.70%
        return "ratio%"
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
        if needs_fallback(answer, sources.summary):
            answer = await fallback_answer(answer.resolved_question or question, sources.summary, sources.index, answer)
    finally:
        stop_collecting_drafts(token)
    return answer
