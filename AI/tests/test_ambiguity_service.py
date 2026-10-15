import asyncio

from app.agent import create_default_tool_registry
from app.agent.query.ambiguity_metrics import metric_candidates
from app.agent.query.ambiguity_tables import table_candidates
from app.agent.query.intent_models import QuestionIntent
from app.agent.query.service import WorkbookQuestionService
from app.agent.query.tabular_catalog import build_query_tables
from app.agent.query.tabular_query_models import TabularQueryPlan
from app.services.workbook_parsing.models import WorkbookSummary
from tests.test_ambiguity_tables import _parallel
from tests.test_metric_observation_answers import _index, _report
from tests.tabular_query_fixtures import table_fixture
from app.agent.query.ambiguity_answers import ambiguous_source_answer


class _Generator:
    async def generate(self, *args):
        raise AssertionError("Clarification and source-bound follow-up must not generate guesses")


class _Classifier:
    def __init__(self, intent):
        self.intent = intent

    async def classify(self, *args):
        return self.intent


def _service(intent):
    return WorkbookQuestionService(_Generator(), create_default_tool_registry(),
                                   classifier=_Classifier(intent))


def test_classifier_cannot_choose_an_ambiguous_table_or_invent_user_scope():
    summary, index = _parallel()
    table = build_query_tables(summary)[0]
    plan = TabularQueryPlan(operation="numeric_summary", table_id=table.id,
                            column_ids=["C"], statistic="sum")
    intent = QuestionIntent(False, "aggregation", ("Owner", "Alpha Holdings"), True, plan)
    answer = asyncio.run(_service(intent).answer("Amount 합계는?", summary, index))
    assert answer.status == "insufficient_evidence"
    assert answer.verification.level == "unverified"
    assert "B4:C6" in answer.answer and "G4:H6" in answer.answer
    assert "합계 30" not in answer.answer


def test_copied_table_clarification_followup_resolves_through_service():
    summary, index = _parallel()
    candidate = table_candidates("Amount 합계는?", summary, index)[0]
    table = build_query_tables(summary)[0]
    plan = TabularQueryPlan(operation="numeric_summary", table_id=table.id,
                            column_ids=["C"], statistic="sum")
    intent = QuestionIntent(False, "aggregation", (), True, plan)
    answer = asyncio.run(_service(intent).answer(candidate.followup, summary, index))
    assert answer.status == "answered"
    assert answer.verification.level == "request_checked"
    assert "합계 30" in answer.answer


def test_copied_exact_cell_period_clarification_resolves_through_service():
    summary = WorkbookSummary("renamed.xlsx", 0, [])
    index = _index({"Results": _report()})
    intent = QuestionIntent(False, "cell_lookup", (), True)
    service = _service(intent)
    question = "2024년 9월 30일 Operating Income은?"
    initial = asyncio.run(service.answer(question, summary, index))
    assert initial.status == "insufficient_evidence"
    candidate = metric_candidates(question, index)[1]
    answer = asyncio.run(service.answer(candidate.followup, summary, index))
    assert answer.status == "answered" and "180" in answer.answer
    assert answer.verification.level == "request_checked"


def test_valid_unique_snapshot_is_not_overridden_by_table_shaped_report_slices():
    summary, index = table_fixture([
        (1, 1, [["Amounts in USD millions"]]), (3, 1, [["Total Debt", 75]]),
        (8, 5, [["+ Total Debt", "Earlier history"], [10, "Prior"], [20, "Later"]]),
        (15, 5, [["+ Total Debt", "Other history"], [30, "Prior"], [40, "Later"]]),
    ])
    question = "총부채(Total Debt)는 얼마야? 단위도 알려줘."
    intent = QuestionIntent(False, "cell_lookup", (), True)
    assert table_candidates(question, summary, index)
    assert ambiguous_source_answer(question, summary, index, intent) is None
    answer = asyncio.run(_service(intent).answer(question, summary, index))
    assert answer.status == "answered" and "75백만 미국 달러" in answer.answer
    assert answer.verification.level == "request_checked"
