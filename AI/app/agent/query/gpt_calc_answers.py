"""The last resort for a question nothing answered: GPT chooses a calculation, code runs it.

GPT names the calculation over the whole table (or over cells it cites), code computes it from the
source, and the answer states the calculation so it can be checked. If none runs, GPT's draft is shown, marked.
Questions answered before, and questions that ask back with options, never reach this.
"""
import asyncio
from contextvars import ContextVar

from openpyxl.utils import range_boundaries

from app.agent.query.gpt_calc_answer_text import cells_answer, table_answer, unverified_draft
from app.agent.query.gpt_calc_cells import evaluate
from app.agent.query.gpt_calc_draft_check import source_references, source_values
from app.agent.query.gpt_calc_checks import fitting_table, listed_cells, plan_problem, unlisted_note, with_cell_values
from app.agent.query.group_rows import group_rows, section_rows
from app.agent.query.models import QuestionAnswerStatus
from app.agent.query.quota_errors import raise_for_quota_exhaustion
from app.agent.query.references import normalize_reference
from app.agent.query.tabular_catalog import build_query_tables
from app.agent.query.tabular_explicit_scope import explicit_ranges

_DRAFTS: ContextVar[list | None] = ContextVar("generated_drafts", default=None)


def start_collecting_drafts():
    return _DRAFTS.set([])


def stop_collecting_drafts(token):
    _DRAFTS.reset(token)


def keep_draft(draft, execution):
    if (drafts := _DRAFTS.get()) is not None:
        drafts.append((draft, source_values(execution), source_references(execution)))


# Answers written by GPT from about 30 searched rows: totals, rates and lists over a whole table need
# every row, so a calculation over the table is preferred when one runs.
_UNLISTED = "The table calculation named a column the table does not list, or left no row: name listed columns."
_SEARCHED = {"search_workbook_data", "inspect_semantic_structure", "recover_formula_values"}


def needs_fallback(answer):
    if answer.clarification_options or "clarify_source_scope" in answer.selected_tools:
        return False  # asking back is an answer the user chooses from
    return answer.status == QuestionAnswerStatus.INSUFFICIENT_EVIDENCE or bool(answer.selected_tools) and set(
        answer.selected_tools) <= _SEARCHED and answer.verification.level != "request_checked"


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
    tables = [table for table in every if table.complete and table.rows]
    if scopes := explicit_ranges(question):  # "'MYE2 - Persons'!A8:CQ412 범위의 …": only that range
        tables = [table for table in tables if any(table.sheet_name == sheet and _overlaps(table.reference, cells)
                                                   for sheet, cells in scopes)]
    labels = {normalize_reference(column.header_reference) for table in every for column in table.columns}
    labels |= {normalize_reference(cell.reference) for row in index.rows if _year_row(row) for cell in row.cells}
    if not tables:
        return None
    from app.agent.query.gpt_calc_planner import LangChainCalcPlanner
    if (planner := planner or LangChainCalcPlanner.from_environment()) is None:
        return None
    cells = {normalize_reference(cell.reference): cell for row in index.rows for cell in row.cells}
    listed = listed_cells(tables, cells)  # kind=cells may cite only the rows GPT was shown
    headings = {table.id: {**section_rows(table), **group_rows(table, summary)} for table in tables}
    note = ""
    for _ in range(2):  # one retry, told what did not run
        try:
            plan = await planner.plan(question, tables, note, headings)
        except Exception as exception:  # a plan cut off at the length limit is asked for once more, shorter
            raise_for_quota_exhaustion(exception)
            note = "The previous plan was cut off at the length limit: write a short plan with few filters."
            continue
        table = fitting_table(tables, plan.table.table, plan.table) if plan.kind == "table" and plan.table else None
        if plan.kind == "table" and plan.table is not None and table is not None:
            from app.agent.query.gpt_calc_tables import run_table
            if not note and (problem := plan_problem(question, table, plan.table, headings.get(table.id))):
                note = problem
                continue
            plan = plan.model_copy(update={"table": with_cell_values(plan.table, cells, question)})  # "> [Table!B66]"
            result = await asyncio.to_thread(run_table, table, plan.table, headings.get(table.id))
            echo = plan.table.aggregate == "count" and len(result.groups) == 1 and result.groups[0][1] == 1 \
                and result.groups[0][0] != "전체" if result is not None else False  # one name back, no figure
            if result is not None and not echo and (result.groups or plan.table.pick not in {"nth", "top"}):
                return table_answer(question, plan, table, result, _style(table, result, plan.table), cells)
            note = _UNLISTED
        elif plan.kind == "cells" and plan.cells is not None and plan.cells.items:
            computed = [(item, evaluate(item.expression, listed, labels)) for item in plan.cells.items]
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

def _overlaps(first, second):
    a, b, c, d = range_boundaries(first.replace("$", ""))
    e, f, g, h = range_boundaries(second.replace("$", ""))
    return a <= g and e <= c and b <= h and f <= d


def _year_row(row):
    """A row of consecutive years (2021, 2022, 2023) names columns even where no table header was read."""
    years = [cell.value for cell in row.cells if isinstance(cell.value, (int, float)) and not isinstance(cell.value, bool)]
    return len(years) >= 3 and all(float(year).is_integer() and 1900 <= year <= 2100 for year in years) \
        and all(later - earlier == 1 for earlier, later in zip(years, years[1:]))


def _style(table, result, calc):
    if calc.aggregate == "ratio":
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
        if needs_fallback(answer):
            answer = await fallback_answer(answer.resolved_question or question, sources.summary, sources.index, answer)
    finally:
        stop_collecting_drafts(token)
    return answer
