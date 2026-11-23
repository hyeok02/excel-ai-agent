"""Rows under one section heading ("Year 2026" over its months) and bounds read as Korean states them."""
import asyncio
from io import BytesIO

from openpyxl import Workbook

from app.agent.query.gpt_calc_answers import fallback_answer
from app.agent.query.gpt_calc_checks import inclusive
from app.agent.query.gpt_calc_models import CalcFilter
from app.agent.query.question_index import build_question_data_index
from app.services.workbook_parser import parse_workbook
from tests.test_gpt_calc_fallback import NOTHING, _Planner, _table


def test_the_months_under_one_year_heading_are_kept_and_the_headings_are_listed():
    book = Workbook()
    book.active.title = "Gen"
    for row in [["Period", "Coal", "Gas"], ["Year 2025", None, None], ["January", 10, 1], ["February", 20, 2],
                ["Year 2026", None, None], ["January", 30, 3], ["February", 40, 4]]:
        book.active.append(row)
    stream = BytesIO()
    book.save(stream)
    summary = parse_workbook("g.xlsx", stream.getvalue())
    index = build_question_data_index("g.xlsx", stream.getvalue(), summary)
    planner = _Planner({"kind": "table", "method": "2026년 1~2월 Coal 합계", "cells": None, "table": _table(
        measure="Coal", filters=[{"column": "Period", "op": "under", "value": "Year 2026"}])})
    planner.plans[0]["table"]["table"] = 0
    answer = asyncio.run(fallback_answer("q", summary, index, NOTHING, planner)).answer
    assert "Coal 합계: 70" in answer  # 30 + 40, not the 2025 months
    assert "Year 2025" in answer.split("(")[-1]  # the headings are left out, as stated


def test_a_korean_bound_includes_the_period_it_names():
    after = inclusive("2020년 이후 입사한 직원", CalcFilter(column="입사일", op="ge", value="2021-01-01"))
    assert (after.op, after.value) == ("ge", "2020")
    before = inclusive("2024년 3월까지 매출", CalcFilter(column="날짜", op="lt", value="2024-04-01"))
    assert (before.op, before.value) == ("le", "2024-03")
    other = CalcFilter(column="입사일", op="ge", value="2015-01-01")
    assert inclusive("2020년 이후 입사한 직원", other) is other  # a bound the question does not name stays


def test_a_plan_ignoring_the_section_the_question_names_is_sent_back():
    from app.agent.query.gpt_calc_checks import plan_problem
    from app.agent.query.gpt_calc_models import TableCalc
    calc = TableCalc.model_validate(_table(measure="Coal"))
    from types import SimpleNamespace
    table, headings = SimpleNamespace(columns=[], rows=[]), {2: "Year 2025", 5: "Year 2026"}
    assert "Year 2026" in plan_problem("2026년 1~2월 합계", table, calc, headings).split("under")[0]
    assert plan_problem("1~2월 합계", table, calc, headings) is None


def test_a_row_formula_is_not_sent_back_for_the_add_it_replaces():
    from types import SimpleNamespace
    from app.agent.query.gpt_calc_checks import plan_problem
    from app.agent.query.gpt_calc_models import TableCalc
    calc = TableCalc.model_validate(_table(measure="E", row_formula="[E]+[F]", add=["B", "C"], aggregate="ratio",
                                           denominator="B+C+E+F"))
    assert plan_problem("불만 비율", SimpleNamespace(columns=[], rows=[]), calc) is None


def test_a_share_whose_whole_was_listed_in_add_is_taken_of_that_whole():
    from tests.test_gpt_calc_more import _ask
    share = _ask({"measure": "국어", "row_formula": "[C]", "aggregate": "ratio", "denominator": "수학", "add": ["국어", "수학"]})
    assert "비율: 49.17%" in share  # 국어 325 of 국어 + 수학 661, not of 수학 alone


def test_a_month_written_as_a_timestamp_names_its_month():
    from app.agent.query.gpt_calc_filters import _matches
    item = CalcFilter(column="Date", op="month", value="2022-12T00:00:00.000Z")
    assert _matches("2022-12-05", item) and not _matches("2023-12-05", item)
