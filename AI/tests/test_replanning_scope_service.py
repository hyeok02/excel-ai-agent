"""Real service recovery preserves cross-table requests and ordinary sum wording."""
import asyncio

import pytest

from app.agent import create_default_tool_registry
from app.agent.query.intent_models import QuestionIntent
from app.agent.query.models import QuestionAnswerDraft
from app.agent.query.service import WorkbookQuestionService
from app.agent.query.tabular_catalog import build_query_tables
from app.agent.query.tabular_query_models import TabularFilter, TabularQueryPlan
from tests.support.replanning_adversarial import NoGeneration, Planner
from tests.tabular_query_fixtures import table_fixture


@pytest.mark.parametrize("question", [
    "고객 표와 연결해서 Orion의 Net Amount 알려줘",
    "Join with customer data and show Net Amount for Orion",
])
def test_missing_join_plan_cannot_be_repaired_as_verified_single_table_lookup(question):
    summary, index = table_fixture([(4, 2, [
        ["Account", "Territory", "Net Amount"],
        ["Orion", "North", 17], ["Other", "South", 90],
    ])], sheet_name="Ledger")
    [table] = build_query_tables(summary)
    plan = TabularQueryPlan(operation="lookup", table_id=table.id, column_ids=["D"],
                            filters=[TabularFilter(column_id="B", operator="equals", value="Orion")])
    first = QuestionIntent(False, "other", from_model=True)
    revised = QuestionIntent(False, "cell_lookup", from_model=True, tabular_query=plan)

    class Generator:
        def __init__(self):
            self.contexts = []

        async def generate(self, original, filename, context):
            self.contexts.append((original, context))
            return QuestionAnswerDraft(answer="연결 대상을 확인하지 못했습니다.", confidence=0, evidence=[])

    class InitialOnly:
        async def classify(self, original, summary):
            return first

    def answer(planner, generator):
        service = WorkbookQuestionService(generator, create_default_tool_registry(), classifier=planner)
        return asyncio.run(service.answer(question, summary, index))

    planner, generator = Planner(first, revised), Generator()
    result = answer(planner, generator)
    baseline_generator = Generator()
    baseline = answer(InitialOnly(), baseline_generator)
    assert result.model_dump() == baseline.model_dump()
    assert result.verification.level != "request_checked"
    assert "plan_replanned" not in result.verification.checks
    assert planner.repairs == [] and planner.questions == [question]
    assert generator.contexts == baseline_generator.contexts


@pytest.mark.parametrize("question", ["combined total of Amount", "combined sum of Amount"])
def test_combined_total_is_an_ordinary_single_table_sum_recovery(question):
    summary, index = table_fixture([(4, 2, [
        ["Account", "Region", "Amount"],
        ["Orion", "North", 17], ["Other", "South", 90], ["Maple", "North", 31],
    ])], sheet_name="Ledger")
    [table] = build_query_tables(summary)
    plan = TabularQueryPlan(operation="numeric_summary", table_id=table.id,
                            column_ids=["D"], statistic="sum")
    planner = Planner(QuestionIntent(False, "other", from_model=True),
                      QuestionIntent(False, "aggregation", from_model=True, tabular_query=plan))
    service = WorkbookQuestionService(NoGeneration(), create_default_tool_registry(), classifier=planner)
    result = asyncio.run(service.answer(question, summary, index))
    assert result.status == "answered" and result.verification.level == "request_checked"
    assert {"request_alignment", "plan_replanned"} <= set(result.verification.checks)
    assert "138" in result.answer and len(planner.repairs) == 1
