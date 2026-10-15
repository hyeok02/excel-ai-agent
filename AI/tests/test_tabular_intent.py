from app.agent.query.intent_models import QuestionIntent, QuestionIntentDraft
from app.agent.query.tabular_query_models import TabularQueryPlan
from app.agent.query.tabular_routing import planned_tabular_answer
from app.agent.query.models import QuestionAnswerStatus
from app.services.workbook_parsing.models import WorkbookSummary
from app.agent.query.index import WorkbookDataIndex
from app.agent.query.service import WorkbookQuestionService
from tests.tabular_query_fixtures import table_fixture


def test_explicit_plan_cannot_be_replaced_by_whole_file_summary():
    plan = TabularQueryPlan(
        operation="frequencies", table_id="Inventory!A1:C20", column_ids=["C"]
    )
    intent = QuestionIntent.from_draft(QuestionIntentDraft(
        scope="whole_workbook", kind="summary", tabular_query=plan,
    ))

    assert intent.tabular_query == plan
    assert not intent.whole_workbook
    assert not intent.wants_a_summary


def test_invalid_source_selection_does_not_silently_return_file_overview():
    plan = TabularQueryPlan(
        operation="frequencies", table_id="Invented!A1:C20", column_ids=["C"]
    )
    answer = planned_tabular_answer(
        QuestionIntent(False, "summary", (), True, plan),
        WorkbookSummary("other.xlsx", 0, []),
        WorkbookDataIndex("other.xlsx", (), 0, False),
        "선택한 속성의 분포를 알려줘",
    )

    assert answer.status == QuestionAnswerStatus.INSUFFICIENT_EVIDENCE
    assert not answer.evidence


def test_legacy_intent_has_no_execution_plan():
    intent = QuestionIntent.from_draft(QuestionIntentDraft(
        scope="whole_workbook", kind="summary", targets=[],
    ))
    assert intent.wants_a_summary
    assert intent.tabular_query is None


def test_lookup_or_comparison_cannot_be_replaced_by_an_aggregate():
    for kind in ("cell_lookup", "comparison", "structure", "row_list"):
        for operation in ("frequencies", "numeric_summary", "row_count"):
            intent = QuestionIntent.from_draft(QuestionIntentDraft(
                scope="specific", kind=kind, tabular_query=TabularQueryPlan(
                    operation=operation, table_id="Data!A1:C10", column_ids=["C"],
                ),
            ))
            assert intent.tabular_query is None
            assert not intent.wants_a_summary
import asyncio
import json

from app.agent import create_default_tool_registry
from app.agent.query.intent_prompts import build_intent_prompt


def test_prompt_includes_real_table_headers_without_semantic_column_schemas():
    summary, _ = table_fixture([(5, 3, [
        ["Record", "Review phase"], ["A", "pending"], ["B", "done"],
    ])])
    assert not summary.sheets[0].column_schemas
    prompt = build_intent_prompt("Review phase별 건수", summary)
    payload = json.loads(prompt.split("<question_input>\n")[1].split("\n</question_input>")[0])
    table = payload["tables"][0]
    assert table["table_id"] == "Arbitrary!C5:D7"
    assert table["columns"][1]["header"] == "Review phase"
    assert table["columns"][1]["samples"] == ["pending", "done"]


def test_scoped_aggregate_bypasses_file_overview_and_generative_trimming():
    summary, index = table_fixture([(1, 1, [
        ["Record", "North. Annex", "Other"], ["A", "pass", "unrelated"],
        ["B", "hold", "unrelated"], ["C", None, "unrelated"],
    ])])
    plan = TabularQueryPlan(
        operation="frequencies", table_id="Arbitrary!A1:C4", column_ids=["B"],
    )

    class Classifier:
        async def classify(self, question, summary):
            return QuestionIntent(False, "aggregation", (), True, plan)

    class Generator:
        async def generate(self, *args):
            raise AssertionError("Source-computed plan must answer directly")

    service = WorkbookQuestionService(
        Generator(), create_default_tool_registry(), classifier=Classifier(),
    )
    answer = asyncio.run(service.answer("North. Annex별 건수", summary, index))
    assert answer.status == QuestionAnswerStatus.ANSWERED
    assert "‘North. Annex’" in answer.answer
    assert "‘pass’ 1건" in answer.answer and "빈칸 1건" in answer.answer
    assert "Other" not in answer.answer and "unrelated" not in answer.answer
