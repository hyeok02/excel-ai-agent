"""A source relationship remains answerable without model-authored equivalence."""
import asyncio

import pytest

from app.agent import create_default_tool_registry
from app.agent.query.header_relation_models import HeaderRelationPlan
from app.agent.query.intent_models import QuestionIntent, QuestionIntentDraft
from app.agent.query.models import QuestionAnswerDraft
from app.agent.query.service import WorkbookQuestionService
from app.agent.query.tabular_catalog import build_query_tables
from app.agent.query.tabular_query_models import TabularQueryPlan
from tests.tabular_query_fixtures import table_fixture


class UnsafeGenerator:
    def __init__(self):
        self.called = False

    async def generate(self, *args):
        self.called = True
        return QuestionAnswerDraft(answer="TCK와 성수계전 작업은 같은 작업입니다.",
                                   evidence=["Arbitrary!B1"], confidence=1)


class Classifier:
    def __init__(self, mode, plan=None):
        self.mode, self.plan = mode, plan

    async def classify(self, *args):
        if self.mode == "failure":
            raise RuntimeError("Classifier unavailable")
        kind = "other" if self.mode == "vague_kind" else "field_relation"
        return QuestionIntent(False, kind, from_model=True, header_relation=self.plan)


@pytest.mark.parametrize("mode", ["vague_kind", "failure", "no_plan", "explicit_plan"])
def test_service_uses_source_header_explanation_despite_classifier_failure_or_vague_kind(mode):
    summary, index = table_fixture([(1, 1, [
        ["Record", "TCK,성수계전 작업"], ["R1", "yes"], ["R2", "no"],
    ])])
    table = build_query_tables(summary)[0]
    plan = HeaderRelationPlan(table_id=table.id, column_ids=["B"], mentions=["TCK", "성수계전 작업"])
    generator = UnsafeGenerator()
    service = WorkbookQuestionService(generator, create_default_tool_registry(),
                                       classifier=Classifier(mode, plan if mode == "explicit_plan" else None))
    result = asyncio.run(service.answer("TCK와 성수계전 작업이 똑같은거야?", summary, index))
    assert not generator.called
    assert result.status == "limited"
    assert result.verification.level == "source_checked"
    assert "하나의 열" in result.answer and "TCK,성수계전 작업" in result.answer
    assert "같은 작업입니다" not in result.answer
    assert any(item.reference == "B1" and item.value == "TCK,성수계전 작업" for item in result.evidence)


def test_unresolved_explicit_field_relation_clarifies_without_model_guess():
    summary, index = table_fixture([(1, 1, [
        ["Record", "Notes"], ["R1", "TCK,성수계전 작업"], ["R2", "other"],
    ])])
    generator = UnsafeGenerator()
    service = WorkbookQuestionService(generator, create_default_tool_registry(), classifier=Classifier("no_plan"))
    result = asyncio.run(service.answer("TCK와 성수계전 작업이 똑같은거야?", summary, index))
    assert not generator.called
    assert result.status == "insufficient_evidence"
    assert result.verification.level == "unverified"
    assert "같은 작업입니다" not in result.answer


def test_field_relation_draft_round_trip_keeps_plan_but_never_whole_file_or_numeric_query():
    relation = HeaderRelationPlan(table_id="Arbitrary!A1:B3", column_ids=["B"],
                                  mentions=["Orion", "Vega 작업"])
    draft = QuestionIntentDraft(scope="whole_workbook", kind="field_relation", header_relation=relation,
                                tabular_query=TabularQueryPlan(operation="row_count", table_id=relation.table_id))
    restored = QuestionIntentDraft.model_validate_json(draft.model_dump_json())
    intent = QuestionIntent.from_draft(restored)
    assert intent.header_relation == relation
    assert not intent.whole_workbook and not intent.wants_a_summary
    assert intent.tabular_query is None and intent.relational_query is None


def test_field_relation_without_plan_stays_specific_instead_of_overview_fallback():
    intent = QuestionIntent.from_draft(QuestionIntentDraft(scope="whole_workbook", kind="field_relation"))
    assert intent.header_relation is None
    assert not intent.whole_workbook and not intent.wants_a_summary
    assert intent.tabular_query is None and intent.relational_query is None
