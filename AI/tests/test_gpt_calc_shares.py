"""A share of some rows in all rows, asked as a ratio without another column."""
from tests.test_gpt_calc_fallback import _ask, _table


def test_a_share_of_the_filtered_rows_is_their_part_of_all_rows():
    east = _ask({"kind": "table", "method": "East의 Amount 비중", "cells": None,
                 "table": _table(filters=[{"column": "Region", "op": "eq", "value": "East"}], aggregate="ratio")})
    assert "비율: 58.82% (Amount 200 / 전체 340)" in east.answer
    rows = _ask({"kind": "table", "method": "East 행 비율", "cells": None,
                 "table": _table(filters=[{"column": "Region", "op": "eq", "value": "East"}], measure=None,
                                 aggregate="ratio")})
    assert "비율: 50.00% (행 수 3 / 전체 6)" in rows.answer


def test_a_total_row_named_by_a_filter_is_read():
    from io import BytesIO
    import asyncio
    from openpyxl import Workbook
    from app.agent.query.gpt_calc_answers import fallback_answer
    from app.agent.query.question_index import build_question_data_index
    from app.services.workbook_parser import parse_workbook
    from tests.test_gpt_calc_fallback import NOTHING, _Planner
    book = Workbook()
    book.active.title = "Sales"
    for row in [["Gas", "Amount"], ["CO2", 300], ["Methane", 50], ["Total emissions", 350]]:
        book.active.append(row)
    stream = BytesIO()
    book.save(stream)
    summary = parse_workbook("g.xlsx", stream.getvalue())
    index = build_question_data_index("g.xlsx", stream.getvalue(), summary)
    plan = {"kind": "table", "method": "Total 행의 Amount", "cells": None,
            "table": _table(filters=[{"column": "Gas", "op": "eq", "value": "Total emissions"}])}
    answer = asyncio.run(fallback_answer("q", summary, index, NOTHING, _Planner(plan)))
    assert "Amount 값: 350" in answer.answer


def test_alike_conditions_are_alternatives_and_quarters_are_read():
    q1 = {"kind": "table", "method": "1·2월", "cells": None, "table": _table(filters=[
        {"column": "Date", "op": "month", "value": "2023-01"}, {"column": "Date", "op": "month", "value": "2023-02"}])}
    assert "Amount 합계: 100" in _ask(q1).answer  # 70 + 30
    quarter = {"kind": "table", "method": "2023 1분기", "cells": None,
               "table": _table(filters=[{"column": "Date", "op": "quarter", "value": "2023-q1"}])}
    assert "Amount 합계: 190" in _ask(quarter).answer
    since = {"kind": "table", "method": "2023-02 이후", "cells": None,
             "table": _table(filters=[{"column": "Date", "op": "ge", "value": "2023-02"}])}
    assert "적용 조건: Date ≥ 2023-02\nAmount 합계: 130" in _ask(since).answer  # 30 + 90 + 10


def test_a_filter_compares_with_a_named_cell_and_an_unnamed_extreme_is_sent_back():
    above = {"kind": "table", "method": "Amount > B2(100)", "cells": None,
             "table": _table(filters=[{"column": "Amount", "op": "ge", "value": "[Sales!D3]"}], measure=None,
                             aggregate="count")}
    assert "행 건수: 4" in _ask(above).answer  # 100, 40, 70 and 90 are at least the 40 in D3
    above["table"]["filters"][0]["op"] = "ge_column"  # a cell written as if it were a column
    assert "행 건수: 4" in _ask(above).answer
    extreme = {"kind": "table", "method": "최댓값", "cells": None, "table": _table(aggregate="max")}
    named = {"kind": "table", "method": "Region별 최댓값", "cells": None,
             "table": _table(group_by=["Region"], aggregate="max", order="desc", pick="top", n=1)}
    assert "1. East: 100" in _ask(extreme, named).answer


def test_sum_and_average_over_a_range_are_written_out_cell_by_cell():
    items = [{"label": "합계", "expression": "SUM(Months!B2:B4)"}, {"label": "평균", "expression": "AVERAGE([Months!C2:C4])"}]
    answer = _ask({"kind": "cells", "method": "범위 합계·평균", "table": None, "cells": {"items": items, "keep": "all"}})
    assert "· 합계: SUM(Months!B2:B4) = 60" in answer.answer and "Months!B4: 30" in {item.label for item in answer.evidence}
    assert "= 19.33" in answer.answer



def _quarters_answer(plan):
    from io import BytesIO
    import asyncio
    from openpyxl import Workbook
    from app.agent.query.gpt_calc_answers import fallback_answer
    from app.agent.query.question_index import build_question_data_index
    from app.services.workbook_parser import parse_workbook
    from tests.test_gpt_calc_fallback import NOTHING, _Planner
    book = Workbook()
    for row in [["Category", "Q1", "Q2", "Q3", "Q4"], ["Web", 105, 9, 8, 52], ["Delivery", 70, 80, 81, 82],
                ["App", 20, 21, 22, 23]]:
        book.active.append(row)
    stream = BytesIO()
    book.save(stream)
    summary = parse_workbook("q.xlsx", stream.getvalue())
    index = build_question_data_index("q.xlsx", stream.getvalue(), summary)
    return asyncio.run(fallback_answer("q", summary, index, NOTHING, _Planner(plan))).answer


def test_columns_added_in_each_row_give_a_row_total_across_columns():
    answer = _quarters_answer({"kind": "table", "method": "Category별 Q1~Q4 합계 최대", "cells": None, "table": _table(
        group_by=["Category"], measure="Q1", add=["Q2", "Q3", "Q4"], order="desc", pick="top", n=1)})
    assert "1. Delivery: 313" in answer  # not Web, the largest Q1 alone
    kinds = _quarters_answer({"kind": "table", "method": "Category 수", "cells": None, "table": _table(
        group_by=["Category"], measure=None, aggregate="count_distinct")})
    assert "Category 서로 다른 값의 수: 3" in kinds
    assert "열별 값: Q1 70 · Q2 80 · Q3 81 · Q4 82" in answer  # one group: each column it added
    every = _quarters_answer({"kind": "table", "method": "Q1 합계", "cells": None, "table": _table(
        filters=[{"column": "Category", "op": "eq", "value": "*"}], measure="Q1")})
    assert "Q1 합계: 195" in every  # "*" names no condition


def test_months_written_as_text_are_read_as_periods():
    from app.agent.query.gpt_calc_filters import _date_part
    assert [_date_part(text, "month") for text in ["December 2025", "Sept 2024", "2025년 3월", "2025.07"]] == [
        "2025-12", "2024-09", "2025-03", "2025-07"]
    assert _date_part("December 2025", "quarter") == "2025-Q4" and _date_part("Spring 2025", "month") is None


def test_a_cut_off_plan_and_a_ratio_with_no_filter_are_asked_again():
    from tests.test_gpt_calc_fallback import _Planner, _workbook, NOTHING, fallback_answer, asyncio

    class Cut(_Planner):
        async def plan(self, question, tables, note="", groups=None):
            if not self.notes:
                self.notes.append(note)
                raise ValueError("length limit reached")
            return await super().plan(question, tables, note, groups)
    east = {"kind": "table", "method": "East 비중", "cells": None,
            "table": _table(filters=[{"column": "Region", "op": "eq", "value": "East"}], aggregate="ratio")}
    planner = Cut(east)
    assert "비율: 58.82%" in asyncio.run(fallback_answer("q", *_workbook(), NOTHING, planner)).answer
    assert "cut off" in planner.notes[1]
    planner = _Planner({**east, "table": _table(aggregate="ratio")}, east)
    assert "비율: 58.82%" in asyncio.run(fallback_answer("q", *_workbook(), NOTHING, planner)).answer
    assert "100%" in planner.notes[1]
