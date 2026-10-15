import asyncio
import json

import pytest

from app.agent import create_default_tool_registry
from app.agent.query.intent_models import QuestionIntent, QuestionIntentDraft
from app.agent.query.intent_prompts import SYSTEM_PROMPT, build_intent_prompt
from app.agent.query.service import WorkbookQuestionService
from app.agent.query.tabular_query_models import TabularQueryPlan
from tests.relational_query_fixtures import relational_fixture, relational_plan


class NoGenerator:
    async def generate(self, *args, **kwargs):
        raise AssertionError("A deterministic relational result must not be rewritten by the model")


@pytest.mark.parametrize("unsafe", [False, True])
def test_service_routes_a_join_or_explicit_failure_without_generator_fallback(unsafe):
    right = [["Customer ID", "Region"], ["C1", "North"], ["C1" if unsafe else "C2", "South"]]
    summary, index = relational_fixture(right=right)
    plan = relational_plan(summary)

    class Classifier:
        async def classify(self, question, summary):
            return QuestionIntent(False, "aggregation", (), True, relational_query=plan)

    service = WorkbookQuestionService(NoGenerator(), create_default_tool_registry(), classifier=Classifier())
    result = asyncio.run(service.answer("Orders와 Customers를 Customer ID로 연결해서 Region별 Amount 합계", summary, index))
    assert result.selected_tools == ["relational_query"]
    assert result.status == ("insufficient_evidence" if unsafe else "answered"), result.answer
    assert result.verification.level == ("unverified" if unsafe else "source_checked")


def test_relational_schema_round_trip_keeps_plan_and_disables_file_overview():
    summary, _ = relational_fixture()
    plan = relational_plan(summary)
    draft = QuestionIntentDraft(scope="whole_workbook", kind="aggregation", relational_query=plan)
    restored = QuestionIntentDraft.model_validate_json(draft.model_dump_json())
    intent = QuestionIntent.from_draft(restored)
    assert intent.relational_query == plan
    assert not intent.whole_workbook and not intent.wants_a_summary
    assert intent.tabular_query is None


def test_incompatible_or_conflicting_plan_types_cannot_bypass_routing_contract():
    summary, _ = relational_fixture()
    plan = relational_plan(summary)
    incompatible = QuestionIntent.from_draft(QuestionIntentDraft(scope="specific", kind="cell_lookup", relational_query=plan))
    assert incompatible.relational_query is None
    conflicting = QuestionIntent.from_draft(QuestionIntentDraft(
        scope="specific", kind="aggregation", relational_query=plan,
        tabular_query=TabularQueryPlan(operation="numeric_summary", table_id=plan.left_table_id, column_ids=["C"])))
    assert conflicting.tabular_query is None and conflicting.relational_query is None


def test_old_schema_without_relational_field_still_parses_and_catalog_contains_both_sources():
    draft = QuestionIntentDraft.model_validate({"scope": "specific", "kind": "aggregation", "targets": []})
    assert QuestionIntent.from_draft(draft).relational_query is None
    summary, _ = relational_fixture()
    prompt = build_intent_prompt("두 표 연결", summary)
    catalog = json.loads(prompt.split("<question_input>\n")[1].split("\n</question_input>")[0])
    assert {table["table_id"] for table in catalog["tables"]} == {"Orders!A1:C3", "Customers!A1:B3"}
    assert "relational_query" in SYSTEM_PROMPT
