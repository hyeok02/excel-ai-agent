"""Shared offline fixtures for missing model plan recovery.

The classifier and answer generator are local stubs. The table catalog,
request alignment, calculation and evidence checks are the production code.
"""
import asyncio
from dataclasses import replace

import pytest

from app.agent import create_default_tool_registry
from app.agent.query.intent_models import QuestionIntent
from app.agent.query.models import QuestionAnswerDraft
from app.agent.query.service import WorkbookQuestionService
from app.agent.query.tabular_catalog import build_query_tables
from app.agent.query.tabular_query_models import TabularFilter, TabularQueryPlan
from tests.tabular_query_fixtures import table_fixture


class Fallback:
    def __init__(self):
        self.calls = []

    async def generate(self, question, filename, execution_context):
        self.calls.append(question)
        return QuestionAnswerDraft(
            answer="일치하는 계산 계획을 찾지 못했습니다.",
            confidence=0,
            evidence=[],
        )


class InitialOnly:
    """The pre-recovery behavior, using exactly the same first intent."""

    def __init__(self, first):
        self.first = first

    async def classify(self, question, summary):
        return self.first


def answer(question, summary, index, planner, generator):
    service = WorkbookQuestionService(
        generator, create_default_tool_registry(), classifier=planner
    )
    return asyncio.run(service.answer(question, summary, index))


@pytest.fixture(params=[
    (4, 2, "Ledger entries", "Account", "Territory", "Net Amount", "Orion", "North", 17, 33),
    (9, 4, "Renamed worksheet", "Project", "Branch", "Quantity", "Maple", "West", 31, 41),
])
def source(request):
    start_row, start_col, sheet, entity, category, measure, name, region, first, last = request.param
    summary, index = table_fixture([(start_row, start_col, [
        [entity, category, measure],
        [name, region, first], ["Other", "Elsewhere", 90], ["Third", region, last],
    ])], sheet_name=sheet)
    summary = replace(summary, filename=f"renamed-{start_row}.xlsx")
    [table] = build_query_tables(summary)
    entity_id, category_id, measure_id = [column.id for column in table.columns]
    aggregate = TabularQueryPlan(
        operation="numeric_summary", table_id=table.id, column_ids=[measure_id], statistic="sum",
        filters=[TabularFilter(column_id=category_id, operator="equals", value=region)],
    )
    lookup = TabularQueryPlan(
        operation="lookup", table_id=table.id, column_ids=[measure_id],
        filters=[TabularFilter(column_id=entity_id, operator="equals", value=name)],
    )
    return dict(summary=summary, index=index, sheet=sheet, start_row=start_row,
                entity_id=entity_id, measure_id=measure_id, entity=entity, category=category,
                measure=measure, name=name, region=region, first=first, total=first + last,
                aggregate=aggregate, lookup=lookup)


def question_for(source, operation, wording=0):
    variants = {
        "aggregate": (
            "{region}의 {measure}는 합계가 얼마야?",
            "{category}가 {region}인 {measure}의 합계를 부탁해",
            "{category}가 {region}인 {measure} 총합 좀 알려줘",
        ),
        "lookup": (
            "{name}의 {measure} 알려줘",
            "{entity}가 {name}인 {measure}의 값을 부탁해",
            "{measure} 중에서 {name}에 해당하는 값은?",
        ),
    }
    return variants[operation][wording].format(**source)


def revised_for(source, operation):
    return QuestionIntent(False, "aggregation" if operation == "aggregate" else "cell_lookup",
                          from_model=True, tabular_query=source[operation])
