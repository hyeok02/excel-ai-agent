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


def test_row_formulas_latest_dates_monthly_means_and_a_column_subtracted_from_itself():
    formula = _ask({"measure": None, "row_formula": "[C]*[D]", "aggregate": "sum"})
    assert "국어*수학 합계: 27,025" in formula  # 5400 + 6650 + 6560 + 8415
    latest = _ask({"measure": "끝", "aggregate": "max"})
    assert "1위 2반 · 다 · 2024-03-01 · 2024-11 · B: 2024-05-30\n" in latest
    monthly = _ask({"group_by": ["월"], "period": "month", "measure": "매출", "then": "mean"})
    assert "위 2개의 평균: 41" in monthly  # (10 + 20) and (30 + 22)
    assert "현재 원본 근거" in _ask({"measure": "매출", "subtract": "매출"})  # 0 for every row is sent back, then refused
    assert "위 1개" not in _ask({"measure": "매출", "then": "sum"})  # one total is not taken together again
    assert "|국어-수학| 값" not in _ask({"measure": "국어", "row_formula": "abs([C]-[D])", "aggregate": "max",
                                       "name_by": "이름"}) and "1위" in _ask({"measure": "국어", "row_formula": "ABS([C]-[D])",
                                                                              "aggregate": "max", "name_by": "이름"})


def test_rows_above_their_own_mean_and_a_formula_dividing_keeps_its_decimals():
    above = _ask({"filters": [{"column": "반", "op": "eq", "value": "1반"}], "measure": "국어", "pick": "above_mean"})
    assert "그룹 평균 80보다 높은 항목 1개" in above and "가" in above
    assert "국어/수학 값: 1.5\n" in _ask({"filters": [{"column": "이름", "op": "eq", "value": "가"}], "measure": None,
                                       "row_formula": "[C]/[D]"})


def test_columns_compared_value_sets_and_figures_beside_a_count():
    across = _ask({"measure": None, "across": ["국어", "수학"], "order": "asc", "pick": "nth", "n": 1})
    assert "1위 국어: 325" in across  # 325 against 336
    sets = _ask({"group_by": ["반"], "bins": [{"name": "앞반", "values": ["1반"]}, {"name": "뒷반", "values": ["2반"]}],
                 "measure": "수학", "aggregate": "mean"})
    assert "· 앞반: 77.5" in sets and "차이(앞반 - 뒷반): -13" in sets
    also = _ask({"filters": [{"column": "수학", "op": "gt", "value": "90"}], "measure": None, "aggregate": "count",
                 "also": [{"label": "초과 점수 합계", "row_formula": "[D]-90"}]})
    assert "행 건수: 2" in also and "초과 점수 합계: 14" in also  # 95 and 99
    days = _ask({"group_by": ["이름"], "measure": None, "row_formula": "DATEDIF([E],[F],\"D\")", "aggregate": "max",
                 "order": "desc", "pick": "nth", "n": 1})
    assert "1위 다: 90" in days


def test_rows_counted_above_their_mean_are_ranked_by_the_score_and_named_once():
    above = _ask({"filters": [{"column": "반", "op": "eq", "value": "2반"}], "measure": "국어", "aggregate": "count",
                  "pick": "above_mean"})
    assert "그룹 평균 82.5보다 높은 항목 1개" in above  # 라 85 against 다 80
    named = _ask({"measure": "수학", "aggregate": "max", "name_by": "이름"})
    assert "1위 라: 99" in named


def test_cells_of_a_table_too_long_to_be_shown_are_not_cited():
    from app.agent.query.gpt_calc_checks import listed_cells
    from app.agent.query.tabular_catalog import build_query_tables
    from tests.test_gpt_calc_fallback import _workbook
    summary, index = _workbook()
    tables = [table for table in build_query_tables(summary) if table.complete and table.rows]
    cells = {cell.reference.casefold(): cell for row in index.rows for cell in row.cells}
    long = [table.__class__(**{**table.__dict__, "rows": table.rows * 30}) for table in tables]
    assert len(listed_cells(tables, cells)) == len(cells) and len(listed_cells(long, cells)) < len(cells)
