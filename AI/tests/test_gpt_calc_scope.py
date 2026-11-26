"""A range the question names is the rows summed, and a retried plan is held to the same check as the first."""
import asyncio

from app.agent.query.gpt_calc_answers import fallback_answer
from tests.test_gpt_calc_fallback import NOTHING, _Planner, _table, _workbook


def _asked(question, *plans):
    summary, index = _workbook()
    planner = _Planner(*plans)
    return asyncio.run(fallback_answer(question, summary, index, NOTHING, planner)), planner


def test_a_named_range_keeps_only_its_rows() -> None:
    answer, _ = _asked("Sales!A1:D3 범위의 Amount 합계는?", {"kind": "table", "method": "Amount 합계", "cells": None, "table": _table()})
    assert "140" in answer.answer and "340" not in answer.answer, answer.answer


def test_a_plan_that_leaves_out_the_named_value_twice_is_not_run() -> None:
    missing = {"kind": "table", "method": "Amount 합계", "cells": None, "table": _table()}
    answer, planner = _asked("Boston의 Amount 합계는?", missing, missing)
    assert "340" not in answer.answer and len(planner.notes) == 2 and planner.notes[1], answer.answer
    boston = {"kind": "table", "method": "Boston 합계", "cells": None, "table": _table(filters=[{"column": "City", "op": "eq", "value": "Boston"}])}
    answer, _ = _asked("Boston의 Amount 합계는?", missing, boston)
    assert "170" in answer.answer, answer.answer


def test_a_named_year_is_held_on_retry_and_a_formula_plan_keeps_to_the_range() -> None:
    boston = [{"column": "City", "op": "eq", "value": "Boston"}]
    plan = lambda filters: {"kind": "table", "method": "Boston 합계", "cells": None, "table": _table(filters=filters)}  # noqa: E731
    answer, _ = _asked("2023년 Boston의 Amount 합계는?", plan(boston), plan(boston))
    assert "170" not in answer.answer, answer.answer  # both years' Boston rows are not 2023's
    answer, _ = _asked("2023년 Boston의 Amount 합계는?", plan(boston),
                       plan([*boston, {"column": "Date", "op": "year", "value": "2023"}]))
    assert "70" in answer.answer and "170" not in answer.answer, answer.answer
    total = "+".join(f"[Sales!D{row}]" for row in range(2, 8))
    formula = {"kind": "cells", "method": "합", "table": None, "cells": {"items": [{"label": "합계", "expression": total}], "keep": "all"}}
    answer, _ = _asked("Sales!A1:D3 범위의 Amount 합계는?", formula)
    assert "340" not in answer.answer, answer.answer


def _years():
    from io import BytesIO
    from openpyxl import Workbook
    from openpyxl.styles import PatternFill
    from app.agent.query.question_index import build_question_data_index
    from app.services.workbook_parser import parse_workbook
    book = Workbook()
    sheet = book.active
    sheet.title = "Monthly"
    sheet.append(["Month", "Amount"])
    for month, amount, heading in [("2022년", None, True), ("1월", 30, False), ("2월", 70, False),
                                   ("2023년", None, True), ("1월", 40, False), ("2월", 30, False)]:
        sheet.append([month, amount])
        if heading:
            sheet.cell(sheet.max_row, 1).fill = PatternFill("solid", fgColor="FFEBF2FA")
    stream = BytesIO()
    book.save(stream)
    summary = parse_workbook("years.xlsx", stream.getvalue())
    return summary, build_question_data_index("years.xlsx", stream.getvalue(), summary)


def test_a_year_named_as_a_section_heading_is_held_on_retry() -> None:
    from tests.test_gpt_calc_headings import _Planner as Headed
    plan = lambda filters: {"kind": "table", "method": "합계", "cells": None, "table": {  # noqa: E731
        **_table(filters=filters), "measure": "Amount"}}
    summary, index = _years()
    every = asyncio.run(fallback_answer("2023년 Amount 합계는?", summary, index, NOTHING, Headed(plan([]), plan([]))))
    assert "170" not in every.answer and "100" not in every.answer, every.answer
    kept = asyncio.run(fallback_answer("2023년 Amount 합계는?", summary, index, NOTHING,
                                       Headed(plan([]), plan([{"column": "Month", "op": "under", "value": "2023년"}]))))
    assert "70" in kept.answer, kept.answer
