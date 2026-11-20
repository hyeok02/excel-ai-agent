"""Group winners by name, sizes of gaps, days between dates, medians, top-n means, period changes and scoped shares."""
import asyncio
from io import BytesIO

from openpyxl import Workbook

from app.agent.query.gpt_calc_answers import fallback_answer
from app.agent.query.question_index import build_question_data_index
from app.services.workbook_parser import parse_workbook
from tests.test_gpt_calc_fallback import NOTHING, _Planner, _table


def _ask(plan):
    book = Workbook()
    book.active.title = "Scores"
    for row in [["반", "이름", "국어", "수학", "시작", "끝", "월", "매장", "매출"],
                ["1반", "가", 90, 60, "2024-01-01", "2024-01-31", "2024-11", "A", 10],
                ["1반", "나", 70, 95, "2024-02-01", "2024-02-11", "2024-12", "A", 30],
                ["2반", "다", 80, 82, "2024-03-01", "2024-05-30", "2024-11", "B", 20],
                ["2반", "라", 85, 99, "2024-04-01", "2024-04-02", "2024-12", "B", 22]]:
        book.active.append(row)
    stream = BytesIO()
    book.save(stream)
    summary = parse_workbook("s.xlsx", stream.getvalue())
    index = build_question_data_index("s.xlsx", stream.getvalue(), summary)
    return asyncio.run(fallback_answer("q", summary, index, NOTHING, _Planner(
        {"kind": "table", "method": "m", "cells": None, "table": _table(**plan)}))).answer


def test_each_groups_top_is_named_and_the_largest_gap_is_its_size():
    top = _ask({"group_by": ["반"], "measure": "수학", "aggregate": "max", "name_by": "이름"})
    assert "· 1반 (나): 95" in top and "· 2반 (라): 99" in top
    gap = _ask({"group_by": ["이름"], "measure": "국어", "subtract": "수학", "absolute": True, "aggregate": "max",
                "order": "desc", "pick": "nth", "n": 1})
    assert "1위 가: 30" in gap  # |90 - 60|, larger than 나's -25


def test_days_between_dates_medians_and_the_mean_of_the_top():
    days = _ask({"group_by": ["이름"], "measure": "끝", "subtract": "시작", "aggregate": "max", "order": "desc",
                 "pick": "nth", "n": 1})
    assert "1위 다: 90" in days
    assert "국어 중앙값: 82.5" in _ask({"measure": "국어", "aggregate": "median"})
    top = _ask({"group_by": ["이름"], "measure": "수학", "order": "desc", "pick": "top", "n": 2, "then": "mean"})
    assert "위 2개의 평균: 97" in top


def test_change_between_periods_per_category_and_a_share_within_a_scope():
    grew = _ask({"group_by": ["매장", "월"], "period": "month", "measure": "매출", "change": True, "order": "desc"})
    assert grew.index("· A: 2024-11 10 → 2024-12 30, +20 (+200.00%)") < grew.index("· B: 2024-11 20")
    share = _ask({"filters": [{"column": "매장", "op": "eq", "value": "A", "scope": True},
                              {"column": "매출", "op": "ge", "value": "20"}], "measure": None, "aggregate": "ratio"})
    assert "비율: 50.00% (행 수 1 / 전체 2)" in share


def test_rows_ranked_by_themselves_two_groups_differ_and_several_columns_are_subtracted():
    top = _ask({"measure": "매출", "aggregate": "mean", "order": "desc", "pick": "top", "n": 2})
    assert "1. 1반 · 나 · 2024-02-01 · 2024-02-11 · 2024-12 · A: 30" in top and "위 2개의 평균: 26" in top
    pair = _ask({"group_by": ["매장"], "measure": "매출"})
    assert "차이(A - B): -2" in pair  # 40 against 42
    net = _ask({"group_by": ["이름"], "measure": "국어", "subtract": "수학", "minus": ["매출"], "order": "desc",
                "pick": "nth", "n": 1})
    assert "1위 가: 20" in net  # 90 - 60 - 10


def test_a_ratio_over_several_columns_and_a_denominator_beside_a_share_are_read():
    both = _ask({"measure": "국어", "aggregate": "ratio", "denominator": "국어, 수학"})
    assert "국어 비율: 49.17%" in both  # 325 of 661
    share = _ask({"group_by": ["반"], "measure": "매출", "denominator": "매출", "share": True})
    assert "· 1반: 40 (48.78%, 2건)" in share


def test_a_plan_naming_no_column_is_told_which_names_are_missing():
    from app.agent.query.gpt_calc_checks import unlisted_note
    from app.agent.query.gpt_calc_models import TableCalc
    from app.agent.query.tabular_catalog import build_query_tables
    from tests.test_gpt_calc_fallback import _workbook
    tables = [table for table in build_query_tables(_workbook()[0]) if table.complete and table.rows]
    calc = TableCalc.model_validate(_table(measure="All Persons", filters=[{"column": "Region", "op": "eq", "value": "x"}]))
    assert "['all persons'] are not columns of table 0" in unlisted_note(tables, 0, calc)
    assert unlisted_note(tables, 0, TableCalc.model_validate(_table())) is None
