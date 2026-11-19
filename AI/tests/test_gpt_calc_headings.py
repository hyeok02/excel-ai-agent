"""Heading rows (regions over their states) are left out of a calculation, read from formatting."""
import asyncio
from io import BytesIO

from openpyxl import Workbook
from openpyxl.styles import PatternFill

from app.agent.query.gpt_calc_answers import fallback_answer
from app.agent.query.gpt_calc_models import CalcPlan
from app.agent.query.question_index import build_question_data_index
from app.services.workbook_parser import parse_workbook
from tests.test_gpt_calc_fallback import NOTHING


def _workbook():
    book = Workbook()
    sheet = book.active
    sheet.title = "Prices"
    sheet.append(["Area", "Price"])
    shade = PatternFill("solid", fgColor="FFEBF2FA")
    for area, price, heading in [("East", 31, True), ("Maine", 32, False), ("Vermont", 24, False),
                                 ("West", 29, True), ("Oregon", 16, False), ("Hawaii", 47, False), ("Idaho", 12, False)]:
        sheet.append([area, price])
        if heading:
            sheet.cell(sheet.max_row, 1).fill = shade
    stream = BytesIO()
    book.save(stream)
    summary = parse_workbook("prices.xlsx", stream.getvalue())
    return summary, build_question_data_index("prices.xlsx", stream.getvalue(), summary)


class _Planner:
    def __init__(self, *plans):
        self.plans, self.notes, self.groups = list(plans), [], None

    async def plan(self, question, tables, note="", groups=None):
        self.notes.append(note)
        self.groups = groups
        return CalcPlan.model_validate(self.plans.pop(0) if len(self.plans) > 1 else self.plans[0])


def _plan(filters, group_by=("Area",)):
    return {"kind": "table", "method": "m", "cells": None, "table": {
        "table": 0, "filters": filters, "group_by": list(group_by), "period": "none", "measure": None,
        "aggregate": "count", "denominator": None, "subtract": None, "order": "none", "pick": "all", "n": 0,
        "share": False}}


def _ask(question, *plans):
    summary, index = _workbook()
    planner = _Planner(*plans)
    return asyncio.run(fallback_answer(question, summary, index, NOTHING, planner)), planner


def test_shaded_heading_rows_are_left_out_unless_named():
    answer, planner = _ask("30 넘는 곳은?", _plan([{"column": "Price", "op": "gt", "value": "30"}]))
    assert "· Maine" in answer.answer and "· Hawaii" in answer.answer and "East" not in answer.answer.split("(")[0]
    assert "상위 구분 행 2개 제외: East, West" in answer.answer
    assert list(next(iter(planner.groups.values())).values()) == ["East", "West"]
    named, _ = _ask("East 가격은?", _plan([{"column": "Area", "op": "eq", "value": "East"}]))
    assert "· East" in named.answer


def test_a_plan_leaving_out_a_value_the_question_names_is_sent_back_once():
    answer, planner = _ask("Oregon 가격은?", _plan([], ()), _plan([{"column": "Area", "op": "eq", "value": "Oregon"}]))
    assert "Oregon" in planner.notes[1] and "· Oregon" in answer.answer and "Maine" not in answer.answer
