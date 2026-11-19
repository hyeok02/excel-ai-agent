"""A question nothing answered is calculated as GPT chooses, by code, over the whole source."""
import asyncio
from io import BytesIO

from openpyxl import Workbook

from app.agent.query.gpt_calc_answers import fallback_answer, needs_fallback
from app.agent.query.gpt_calc_answer_text import unverified_draft
from app.agent.query.gpt_calc_cells import evaluate
from app.agent.query.gpt_calc_models import CalcPlan
from app.agent.query.models import QuestionAnswer, QuestionAnswerDraft
from app.agent.query.question_index import build_question_data_index
from app.services.workbook_parser import parse_workbook

NOTHING = QuestionAnswer(question="q", answer="현재 원본 근거로 확인 가능한 답변이 없습니다.", status="insufficient_evidence",
                         confidence=0, selected_tools=["search_workbook_data"], evidence=[], limitations=[])


def _workbook():
    book = Workbook()
    sales = book.active
    sales.title = "Sales"
    sales.append(["Date", "Region", "City", "Amount"])
    for day, region, city, amount in [("2022-01-03", "East", "Boston", 100), ("2022-05-03", "West", "LA", 40),
                                      ("2023-01-03", "East", "Boston", 70), ("2023-02-03", "East", "NYC", 30),
                                      ("2023-03-03", "West", "LA", 90), ("2023-04-03", "North", "Oslo", 10)]:
        sales.append([day, region, city, amount])
    months = book.create_sheet("Months")
    months.append(["월", "2023", "2024"])
    for row in [["1월", 10, 12], ["2월", 20, 15], ["3월", 30, 31]]:
        months.append(row)
    stream = BytesIO()
    book.save(stream)
    content = stream.getvalue()
    summary = parse_workbook("sales.xlsx", content)
    return summary, build_question_data_index("sales.xlsx", content, summary)


class _Planner:
    def __init__(self, plan):
        self.plan_value, self.seen = plan, None

    async def plan(self, question, tables):
        self.seen = tables
        plan = dict(self.plan_value)
        if plan.get("table"):
            plan["table"] = {**plan["table"], "table": [table.sheet_name for table in tables].index("Sales")}
        return CalcPlan.model_validate(plan)


def _table(**changes):
    return {"table": 0, "filters": [], "group_by": [], "period": "none", "measure": "Amount", "aggregate": "sum",
            "order": "none", "pick": "all", "n": 0, "share": False, **changes}


def _ask(plan):
    summary, index = _workbook()
    return asyncio.run(fallback_answer("q", summary, index, NOTHING, _Planner(plan)))


def test_second_largest_group_is_computed_over_every_row():
    answer = _ask({"kind": "table", "method": "Region별 Amount 합계 2위", "cells": None,
                   "table": _table(group_by=["Region"], order="desc", pick="nth", n=2)})
    assert answer.status == "limited" and "2위 West: 130" in answer.answer
    assert answer.answer.startswith("계산 방식: Region별 Amount 합계 2위") and "6개 행" in answer.answer


def test_years_are_compared_and_distinct_values_counted():
    years = _ask({"kind": "table", "method": "연도별 합계", "cells": None,
                  "table": _table(group_by=["Date"], period="year")})
    assert "· 2022: 140" in years.answer and "· 2023: 200" in years.answer and "+60 (+42.86%)" in years.answer
    cities = _ask({"kind": "table", "method": "City 서로 다른 값", "cells": None,
                   "table": _table(measure="City", aggregate="count_distinct")})
    assert "City 서로 다른 값의 수: 4" in cities.answer


def test_groups_above_the_mean_and_shares():
    answer = _ask({"kind": "table", "method": "City별 합계, 평균 초과", "cells": None,
                   "table": _table(group_by=["City"], order="desc", pick="above_mean", share=True)})
    assert "그룹 평균 85보다 높은 항목 2개" in answer.answer and "Boston: 170 (50.00%)" in answer.answer


def test_cells_are_combined_from_their_own_values_and_filtered():
    items = [{"label": f"{month}월", "expression": f"[Months!C{month + 1}]-[Months!B{month + 1}]"} for month in (1, 2, 3)]
    answer = _ask({"kind": "cells", "method": "월별 2024-2023, 줄어든 달", "table": None,
                   "cells": {"items": items, "keep": "negative"}})
    assert "· 2월: Months!C3(15)-Months!B3(20) = -5" in answer.answer and "1월" not in answer.answer
    assert {item.label.split(":")[0] for item in answer.evidence} >= {"Months!C3", "Months!B3"}


def test_an_unrunnable_plan_or_a_bad_reference_keeps_the_original_answer():
    assert _ask({"kind": "table", "method": "x", "cells": None, "table": _table(measure="Nope")}) is NOTHING
    assert _ask({"kind": "cells", "method": "x", "table": None,
                 "cells": {"items": [{"label": "a", "expression": "[Months!A2]+1"}], "keep": "all"}}) is NOTHING
    assert _ask({"kind": "none", "method": "", "table": None, "cells": None}) is NOTHING


def test_only_arithmetic_is_evaluated():
    _, index = _workbook()
    from app.agent.query.references import normalize_reference
    cells = {normalize_reference(cell.reference): cell for row in index.rows for cell in row.cells}
    assert evaluate("[Months!C2]/[Months!B2]*100", cells)[0] == 120
    assert evaluate("__import__('os')", cells) is None and evaluate("[Months!B2]**2", cells) is None


def test_clarifications_are_left_and_a_declining_draft_is_not_shown():
    asked = NOTHING.model_copy(update={"selected_tools": ["clarify_source_scope"]})
    assert needs_fallback(NOTHING) and not needs_fallback(asked)
    declined = QuestionAnswerDraft(answer="지역별 합계는 확인할 수 없습니다.", confidence=0.3)
    assert unverified_draft("q", NOTHING, declined, [849.0, 783.0]) is None
    drafted = QuestionAnswerDraft(answer="3월에 849에서 783으로 66 줄었습니다(7.77% 감소).", confidence=0.8)
    shown = unverified_draft("q", NOTHING, drafted, [849.0, 783.0])
    assert shown.answer.startswith("[GPT 답변 · 수치 검산]") and shown.status == "limited"
    invented = QuestionAnswerDraft(answer="3월에 849에서 783으로 70 줄었습니다.", confidence=0.8)
    assert unverified_draft("q", NOTHING, invented, [849.0, 783.0]) is None
