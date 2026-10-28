"""A missing plan recovery shares the original context and source limits."""
import asyncio

import pytest

from app.agent import create_default_tool_registry
from app.agent.execution import AgentToolExecutor
from app.agent.query.intent_models import QuestionIntent
from app.agent.query.models import QuestionAnswerDraft
from app.agent.query.question_formula_sources import prepare_formula_sources
from app.agent.query.service import WorkbookQuestionService
from app.agent.query.tabular_catalog import build_query_tables
from app.agent.query.tabular_query_models import TabularFilter, TabularQueryPlan
from app.agent.query.workbook_source_models import SourceReadLimits
from tests.support.large_workbook_fixtures import parsed, tiny_caps, workbook
from tests.support.replanning_adversarial import Planner
from tests.tabular_query_fixtures import table_fixture


class CapturingGenerator:
    def __init__(self):
        self.contexts = []

    async def generate(self, question, filename, execution_context):
        self.contexts.append((question, filename, execution_context))
        return QuestionAnswerDraft(answer="확인할 수 없습니다.", confidence=0)


class CapturingExecutor(AgentToolExecutor):
    def __init__(self):
        super().__init__()
        self.calls = []

    def execute(self, plan, context, registry):
        self.calls.append(context)
        return super().execute(plan, context, registry)


def source():
    summary, index = table_fixture([(4, 2, [
        ["Account", "Territory", "Net Amount"],
        ["Orion", "North", 17], ["Other", "Elsewhere", 90], ["Third", "North", 33],
    ])], sheet_name="Ledger")
    [table] = build_query_tables(summary)
    plan = TabularQueryPlan(operation="lookup", table_id=table.id, column_ids=["D"],
        filters=[TabularFilter(column_id="B", operator="equals", value="Orion")])
    return summary, index, plan


def service(planner):
    generator, executor = CapturingGenerator(), CapturingExecutor()
    return WorkbookQuestionService(generator, create_default_tool_registry(),
        executor=executor, classifier=planner), generator, executor


def test_failed_recovery_keeps_original_execution_context_without_rescanning():
    summary, index, plan = source()
    initial = QuestionIntent(False, "other", from_model=True)
    wrong = plan.model_copy(update={"table_id": "not-the-source"})
    planner = Planner(initial, QuestionIntent(False, "cell_lookup", from_model=True,
                                              tabular_query=wrong))
    retried, generator, executor = service(planner)
    baseline, original_generator, original_executor = service(Planner(initial, None))
    question = "Orion의 Net Amount 알려줘"
    sources = prepare_formula_sources(summary, index)
    result = asyncio.run(retried._answer_prepared(question, sources))
    expected = asyncio.run(baseline._answer_prepared(question, sources, allow_replan=False))

    assert result.model_dump() == expected.model_dump()
    assert generator.contexts == original_generator.contexts
    assert len(generator.contexts) == len(executor.calls) == len(original_executor.calls) == 1
    assert executor.calls[0].intent == initial
    assert len(planner.questions) == len(planner.repairs) == 1
    assert baseline._classifier.repairs == []
    assert "intent_resolution" not in result.selected_tools


def test_true_source_ambiguity_is_not_resolved_by_a_model_retry():
    summary, index = table_fixture([
        (4, 2, [["Company", "Revenue"], ["Alpha", 10], ["Beta", 20]]),
        (4, 7, [["Company", "Revenue"], ["Gamma", 70], ["Delta", 80]]),
    ])
    [table, _] = build_query_tables(summary)
    plan = TabularQueryPlan(operation="numeric_summary", table_id=table.id,
                           column_ids=["C"], statistic="sum")
    planner = Planner(QuestionIntent(False, "other", from_model=True),
        QuestionIntent(False, "aggregation", from_model=True, tabular_query=plan))
    instance, _, _ = service(planner)
    result = asyncio.run(instance.answer("Revenue 합계", summary, index))
    assert result.status == "insufficient_evidence"
    assert result.clarification_options and result.verification.level != "request_checked"
    assert planner.repairs == []


@pytest.mark.parametrize("limits", [SourceReadLimits(max_reads=0),
                                   SourceReadLimits(max_rows=3),
                                   SourceReadLimits(max_cells=35)])
def test_missing_plan_cannot_reset_an_exhausted_stream_budget(tiny_caps, limits):
    summary, index, _ = parsed(workbook({"Records": [
        ["Account", "Territory", "Net Amount"],
        *[[f"Entry{number}", "North", number] for number in range(1, 10)],
    ]}), limits=limits)
    provider, budget = index.source_provider, index.source_provider._budget
    if limits.max_cells == 35:
        with provider.scan_rows("Records", "A1:C3") as scan:
            assert len(list(scan)) == 3
        assert scan.complete
    [table] = build_query_tables(summary)
    plan = TabularQueryPlan(operation="numeric_summary", table_id=table.id,
        column_ids=["C"], statistic="sum", filters=[
            TabularFilter(column_id="B", operator="equals", value="North")])
    planner = Planner(QuestionIntent(False, "other", from_model=True),
        QuestionIntent(False, "aggregation", from_model=True, tabular_query=plan))
    instance, _, _ = service(planner)
    seen_sources = []
    answer_once = instance._answer_once

    async def capture(question, sources, **kwargs):
        seen_sources.append(sources)
        return await answer_once(question, sources, **kwargs)

    instance._answer_once = capture
    result = asyncio.run(instance.answer("North의 Net Amount는 합계가 얼마야?", summary, index))
    assert result.verification.level != "request_checked", result.model_dump()
    assert "plan_replanned" not in result.verification.checks
    assert len(planner.repairs) == 1
    assert len(seen_sources) == 2 and seen_sources[0] is seen_sources[1]
    assert seen_sources[1].index.source_provider is provider and provider._budget is budget
