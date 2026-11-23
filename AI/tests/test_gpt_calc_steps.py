"""Change against the previous period, groups meeting a figure, an item's place, weekdays and halves,
the spread of a column, a column's mean as a bound, rows missing from another table's list, a share of the top."""
from app.agent.query.gpt_calc_filters import _date_part
from tests.test_gpt_calc_more import _ask


def test_each_period_against_the_one_before_and_groups_meeting_a_figure():
    assert "· 2024-12: 22" in _ask({"group_by": ["월"], "period": "month", "measure": "매출",
                                     "versus_previous": "difference"})  # (30 + 22) - (10 + 20)
    kept = _ask({"group_by": ["반"], "measure": "수학", "having": {"op": "ge", "value": 160}})
    assert "반 1개:" in kept and "· 2반: 181" in kept  # 1반's 155 is left out


def test_an_items_place_weekdays_halves_and_the_spread_of_a_column():
    assert "다: 4개 중 3위 (80)" in _ask({"group_by": ["이름"], "measure": "국어", "order": "desc", "rank_of": "다"})
    assert "· 월요일: 2" in _ask({"group_by": ["시작"], "period": "weekday", "measure": None, "aggregate": "count"})
    assert _date_part("2024-08-01", "half") == "2024-H2" and _date_part("2024-03-01", "weekday") == "금요일"
    assert "국어 최댓값과 최솟값의 차이: 20" in _ask({"measure": "국어", "aggregate": "range"})


def test_a_mean_bound_a_list_from_another_column_and_the_share_of_the_top():
    assert "행 건수: 2" in _ask({"filters": [{"column": "국어", "op": "ge", "value": "mean"}], "measure": None,
                              "aggregate": "count"})  # 90 and 85 against 81.25
    missing = _ask({"filters": [{"column": "이름", "op": "not_in", "value": "[Scores!B2:B3]"}], "measure": None,
                    "aggregate": "count"})
    assert "행 건수: 2" in missing and "목록에 없음: 2개 값" in missing
    top = _ask({"group_by": ["이름"], "measure": "매출", "order": "desc", "pick": "top", "n": 2, "then": "sum",
                "share": True})
    assert "위 2개의 합계: 52 (전체의 63.41%)" in top


def test_a_plan_settled_with_itself_and_none_left_counted_as_zero():
    assert "다: 4개 중 3위 (80)" in _ask({"group_by": ["이름"], "measure": "국어", "order": "desc", "rank_of": "다",
                                       "filters": [{"column": "이름", "op": "eq", "value": "다"}]})
    share = _ask({"filters": [{"column": "국어", "op": "ge", "value": "85", "scope": True}], "measure": None,
                  "aggregate": "ratio"})
    assert "비율: 50.00% (행 수 2 / 전체 4)" in share
    assert "행 건수: 0" in _ask({"filters": [{"column": "국어", "op": "gt", "value": "100"}], "measure": None,
                              "aggregate": "count"})
    assert "· 2024-12: 22" in _ask({"group_by": ["월"], "period": "month", "measure": "매출", "subtract": "매출",
                                     "versus_previous": "difference"})


def test_a_bound_written_with_a_time_bounds_its_day():
    from app.agent.query.gpt_calc_filters import _matches
    from app.agent.query.gpt_calc_models import CalcFilter
    until = CalcFilter(column="d", op="le", value="2025-03-15T23:59:59")
    assert _matches("2025-03-15", until) and not _matches("2025-03-16", until)


def test_each_store_against_its_own_previous_month_and_a_timed_korean_bound():
    from app.agent.query.gpt_calc_bounds import inclusive
    from app.agent.query.gpt_calc_models import CalcFilter
    grew = _ask({"group_by": ["매장", "월"], "period": "month", "measure": "매출", "versus_previous": "rate"})
    assert "A · 2024-12: 200" in grew and "B · 2024-12: 10" in grew  # 10 → 30 and 20 → 22
    after = inclusive("2020년 이후 입사", CalcFilter(column="d", op="gt", value="2020-12-31T00:00:00"))
    assert (after.op, after.value) == ("ge", "2020")


def test_excels_power_sign_and_a_previous_period_without_dates():
    assert "1.41" in _ask({"measure": None, "row_formula": "([D]/[D])*2^0.5", "aggregate": "max"})
    assert "현재 원본 근거" in _ask({"group_by": ["매장"], "period": "month", "measure": "매출", "versus_previous": "rate"})


def test_a_period_asked_of_groups_without_dates_adds_the_one_date_column():
    from types import SimpleNamespace as N
    from app.agent.query.gpt_calc_values import with_date_group
    store, day = N(id="A"), N(id="B")
    table = N(columns=[store, day], rows=[N(values={"A": "강남", "B": "2024-11-03"})])
    assert with_date_group(table, [store], "month") == [store, day] and with_date_group(table, [store], "none") == [store]
    grew = _ask({"group_by": ["매장", "월"], "period": "month", "measure": "매출", "versus_previous": "rate"})
    assert "→" not in grew  # two stores' growth rates are not one period after another


def test_a_running_total_up_to_a_month_starts_that_year_and_a_place_shares_a_tie():
    from app.agent.query.gpt_calc_bounds import year_to_date
    from app.agent.query.gpt_calc_filters import _matches
    from app.agent.query.gpt_calc_models import CalcFilter
    until = [CalcFilter(column="월", op="le", value="2025-06")]
    assert [(item.op, item.value) for item in year_to_date("2025년 6월까지 누적 가입자", until)] == [
        ("le", "2025-06"), ("ge", "2025")]
    assert year_to_date("2025년 6월까지 가입자", until) == until  # no 누적, no start added
    assert _matches("2025-03-31", CalcFilter(column="d", op="le", value="03-31"))
    tie = _ask({"group_by": ["이름"], "measure": "매출", "row_formula": "[C]-[C]+1", "order": "desc", "rank_of": "다"})
    assert "공동 1위" in tie


def test_columns_summarized_apart_may_be_combined_by_the_calculation():
    from app.agent.query.gpt_calc_answers import needs_fallback
    from app.agent.query.models import QuestionAnswer, QuestionAnswerVerification
    apart = QuestionAnswer(question="q", answer="‘재고’: 합계 … / ‘안전재고’: 합계 …", status="answered", confidence=1,
                           selected_tools=["tabular_query"], evidence=[], limitations=[],
                           verification=QuestionAnswerVerification(level="request_checked",
                                                                   checks=["calculation", "column_summaries"]))
    assert needs_fallback(apart)
    assert not needs_fallback(apart.model_copy(update={"verification": QuestionAnswerVerification(
        level="request_checked", checks=[])}))
    from app.agent.query.gpt_calc_bounds import year_to_date
    from app.agent.query.gpt_calc_models import CalcFilter
    march = [CalcFilter(column="거래일", op="month", value="2025-03")]
    assert [(item.op, item.value) for item in year_to_date("3월까지 누적 거래 금액", march)] == [
        ("le", "2025-03"), ("ge", "2025")]


def test_a_comma_separated_list_is_a_set_of_values():
    assert "· A: 40" in _ask({"filters": [{"column": "매장", "op": "in", "value": "A, C"}], "group_by": ["매장"],
                               "measure": "매출"})


def test_a_korean_bound_read_as_its_period_alone_is_widened():
    from app.agent.query.gpt_calc_bounds import inclusive
    from app.agent.query.gpt_calc_models import CalcFilter
    after = inclusive("2020년 이후 입사한 직원", CalcFilter(column="입사일", op="year", value="2020"))
    assert (after.op, after.value) == ("ge", "2020")
    until = inclusive("2024년 3월까지 매출", CalcFilter(column="날짜", op="month", value="2024-03"))
    assert (until.op, until.value) == ("le", "2024-03")
    same = CalcFilter(column="입사일", op="year", value="2020")
    assert inclusive("2020년 입사한 직원", same) is same


def test_the_mean_asked_of_single_row_groups_picked_is_their_mean():
    top = _ask({"group_by": ["이름"], "measure": "매출", "aggregate": "mean", "then": "sum", "order": "desc",
                "pick": "top", "n": 2})
    assert "위 2개의 평균: 26" in top  # 30 and 22


def test_cells_written_as_comparisons_keep_the_values_beyond_the_bound():
    from app.agent.query.gpt_calc_models import CalcPlan
    from app.agent.query.gpt_calc_planner import compared_cells
    plan = CalcPlan.model_validate({"kind": "cells", "method": "m", "table": None, "cells": {"items": [
        {"label": "3월", "expression": "[KPI!D2]>0.2"}, {"label": "4월", "expression": "[KPI!E2] > 0.2"}], "keep": "all"}})
    settled = compared_cells(plan).cells
    assert (settled.keep, settled.threshold, settled.items[1].expression) == ("above", 0.2, "[KPI!E2]")
