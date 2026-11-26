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
