import asyncio

from app.agent import create_default_tool_registry
from app.agent.query.conversation_models import ContextResolutionDraft, QuestionConversation
from app.agent.query.intent_models import QuestionIntent
from app.agent.query.service import WorkbookQuestionService
from app.agent.query.tabular_query_models import TabularFilter, TabularQueryPlan
from tests.tabular_query_fixtures import table_fixture


class Generator:
    async def generate(self, *args):
        raise AssertionError("The resolved question must use the source-bound query")


class Resolver:
    def __init__(self, question, context_id="turn:0"):
        self.question, self.context_id, self.seen = question, context_id, None

    async def resolve(self, question, context):
        self.seen = context
        return ContextResolutionDraft(status="resolved", question=self.question,
                                      context_ids=[self.context_id])


class Classifier:
    def __init__(self, plan, kind="aggregation"):
        self.plan, self.kind, self.seen = plan, kind, None

    async def classify(self, question, summary):
        self.seen = question
        return QuestionIntent(False, self.kind, (), True, self.plan)


def fixture():
    return table_fixture([(1, 1, [
        ["장비", "검토 상태", "수량"], ["Unit-A", "x", 10],
        ["Unit-B", "o", 20], ["Unit-C", "x", 30],
    ])], "점검")


def test_followup_filter_is_executed_on_source_not_prior_answer():
    summary, index = fixture()
    resolved = "점검 시트의 검토 상태가 x인 장비를 보여줘"
    resolver = Resolver(resolved)
    classifier = Classifier(TabularQueryPlan(
        operation="row_list", table_id="점검!A1:C4", column_ids=["A"],
        filters=[TabularFilter(column_id="B", operator="equals", value="x")],
    ), "row_list")
    service = WorkbookQuestionService(Generator(), create_default_tool_registry(),
                                     classifier=classifier, context_resolver=resolver)
    context = QuestionConversation(turns=[{
        "question": "검토 상태의 표시별 건수를 알려줘", "evidence": ["점검!B1:B4"],
    }])
    answer = asyncio.run(service.answer("그중 x인 장비를 보여줘", summary, index, context))
    assert classifier.seen == resolved
    assert answer.question == "그중 x인 장비를 보여줘"
    assert answer.resolved_question == resolved
    assert "Unit-A" in answer.answer and "Unit-C" in answer.answer
    assert "Unit-B" not in answer.answer
    assert answer.status == "limited"
    assert answer.verification.level == "source_checked"
    assert "context_resolved" in answer.verification.checks


def test_insight_reference_can_bind_an_implicit_metric_question():
    summary, index = fixture()
    resolver = Resolver("점검 시트의 수량 합계를 알려줘", "insight:0")
    classifier = Classifier(TabularQueryPlan(
        operation="numeric_summary", table_id="점검!A1:C4",
        column_ids=["C"], statistic="sum",
    ))
    service = WorkbookQuestionService(Generator(), create_default_tool_registry(),
                                     classifier=classifier, context_resolver=resolver)
    context = QuestionConversation(insights=[{
        "title": "수량 현황", "topic": "수량", "evidence": ["점검!C1:C4"],
    }])
    answer = asyncio.run(service.answer("그 항목의 합계를 알려줘", summary, index, context))
    assert "60" in answer.answer
    assert answer.resolved_question == resolver.question
    assert "fact" not in resolver.seen[0]["hint"]


def test_missing_context_referent_never_reaches_generator():
    summary, index = fixture()
    service = WorkbookQuestionService(Generator(), create_default_tool_registry(),
                                     context_resolver=Resolver("다른 파일의 수량 합계"))
    context = QuestionConversation(turns=[{
        "question": "다른 파일의 수량은?", "evidence": ["다른파일!C1"],
    }])
    answer = asyncio.run(service.answer("그 합계를 알려줘", summary, index, context))
    assert answer.status == "insufficient_evidence"
    assert answer.selected_tools == ["clarify_question_context"]
    assert answer.verification.level == "unverified"


def test_rewrite_cannot_change_an_explicit_identifier():
    summary, index = fixture()
    service = WorkbookQuestionService(Generator(), create_default_tool_registry(),
                                     context_resolver=Resolver("장비 #1의 수량은?"))
    context = QuestionConversation(turns=[{
        "question": "장비 #1의 수량은?", "evidence": ["점검!A1:C2"],
    }])
    answer = asyncio.run(service.answer("그럼 장비 #99의 수량은?", summary, index, context))
    assert answer.status == "insufficient_evidence"
    assert answer.resolved_question is None


def test_unresolved_latest_turn_cannot_silently_restore_older_subject():
    summary, index = fixture()
    resolver = Resolver("Unit-A의 수량은?", "turn:0")
    service = WorkbookQuestionService(Generator(), create_default_tool_registry(), context_resolver=resolver)
    context = QuestionConversation(turns=[
        {"question": "Unit-A의 수량은?", "evidence": ["점검!A2:C2"]},
        {"question": "Missing-Unit의 수량은?", "evidence": []},
    ])
    answer = asyncio.run(service.answer("그건 얼마야?", summary, index, context))
    assert answer.status == "insufficient_evidence"
    assert answer.selected_tools == ["clarify_question_context"]
