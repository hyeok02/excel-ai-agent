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
