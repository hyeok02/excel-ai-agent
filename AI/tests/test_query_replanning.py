"""Repair bad plans, not missing facts; no live model or answer generator."""
import asyncio

import pytest

from app.agent import create_default_tool_registry
from app.agent.query.intent_models import QuestionIntent
from app.agent.query.service import WorkbookQuestionService
from app.agent.query.tabular_catalog import build_query_tables
from app.agent.query.tabular_query_models import TabularFilter, TabularQueryPlan
from tests.tabular_query_fixtures import table_fixture


class NoGeneration:
    async def generate(self, *args):
        raise AssertionError("Plan repair must never generate a substitute answer")


class Planner:
    def __init__(self, first, second):
        self.first, self.second = first, second
        self.calls, self.repairs = 0, []

    async def classify(self, question, summary):
        self.calls += 1
        return self.first

    async def replan(self, question, summary, feedback):
        self.repairs.append((question, feedback))
        if isinstance(self.second, Exception):
            raise self.second
        return self.second


def intent(plan):
    return QuestionIntent(False, "aggregation", from_model=True, tabular_query=plan)


def fixture(start=1, sheet="Records"):
    summary, index = table_fixture([(start, 1, [
        ["Record", "Region", "Amount"], ["Alpha", "Seoul", 10],
        ["Beta", "Busan", 90], ["Gamma", "Seoul", 30],
    ])], sheet_name=sheet)
    [table] = build_query_tables(summary)
    plan = TabularQueryPlan(operation="numeric_summary", table_id=table.id,
        column_ids=["C"], statistic="average", filters=[
            TabularFilter(column_id="B", operator="equals", value="Seoul")])
    return summary, index, plan


def run(summary, index, planner, question="Region이 Seoul인 Amount 평균"):
    service = WorkbookQuestionService(NoGeneration(), create_default_tool_registry(), classifier=planner)
    return asyncio.run(service.answer(question, summary, index))


@pytest.mark.parametrize("start,sheet", [(1, "Records"), (7, "Renamed table")])
@pytest.mark.parametrize("change,code", [
    ({"table_id": "invented"}, "unknown_table_id"),
    ({"column_ids": ["ZZ"]}, "unknown_or_ambiguous_column_id"),
    ({"filters": []}, "request_scope_or_operation_mismatch"),
    ({"statistic": "sum"}, "request_scope_or_operation_mismatch"),
])
def test_one_repair_computes_original_request(start, sheet, change, code):
    summary, index, plan = fixture(start, sheet)
    planner = Planner(intent(plan.model_copy(update=change)), intent(plan))
    answer = run(summary, index, planner)
    assert answer.status == "answered" and "평균 20" in answer.answer
    assert answer.verification.level == "request_checked"
    assert "plan_replanned" in answer.verification.checks
    assert planner.calls == 1 and len(planner.repairs) == 1
    assert planner.repairs[0][1]["code"] == code
    assert {item.sheet_name for item in answer.evidence} == {sheet}


@pytest.mark.parametrize("second", ["invalid", "missing_condition", "summary", "error"])
def test_retry_cannot_drop_conditions_or_generate_and_cannot_loop(second):
    summary, index, plan = fixture()
    bad = intent(plan.model_copy(update={"table_id": "invented"}))
    revised = {"invalid": bad, "missing_condition": intent(plan.model_copy(update={"filters": []})),
               "summary": QuestionIntent(True, "summary", from_model=True),
               "error": TimeoutError("private provider error")}[second]
    planner = Planner(bad, revised)
    answer = run(summary, index, planner)
    assert answer.status == "insufficient_evidence" and answer.verification.level == "unverified"
    assert planner.calls == 1 and len(planner.repairs) == 1
    assert "private provider" not in answer.answer


def test_good_plan_has_no_extra_invocation():
    summary, index, plan = fixture()
    planner = Planner(intent(plan), AssertionError("unnecessary repair"))
    assert run(summary, index, planner).status == "answered"
    assert planner.calls == 1 and planner.repairs == []


def test_source_currency_conflict_is_not_a_repairable_plan_failure():
    summary, index = table_fixture([(1, 1, [["Item", "Amount", "Currency"],
        ["Alpha", 10, "USD"], ["Beta", 20, "EUR"]])])
    [table] = build_query_tables(summary)
    plan = TabularQueryPlan(operation="numeric_summary", table_id=table.id,
                            column_ids=["B"], statistic="sum")
    planner = Planner(intent(plan), AssertionError("source conflict is not repairable"))
    answer = run(summary, index, planner, "Amount 합계")
    assert answer.status == "insufficient_evidence" and answer.verification.level == "unverified"
    assert planner.repairs == []
