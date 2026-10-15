import asyncio

from app.agent import create_default_tool_registry
from app.agent.query.claim_models import SourceClaim
from app.agent.query.intent_models import QuestionIntent
from app.agent.query.models import QuestionAnswerDraft
from app.agent.query.service import WorkbookQuestionService
from app.agent.query.tabular_query_models import TabularFilter, TabularQueryPlan
from tests.tabular_query_fixtures import table_fixture


class Classifier:
    def __init__(self, table="점검!A1:B3"):
        self.table = table

    async def classify(self, question, summary):
        return QuestionIntent(False, "cell_lookup", (), True, TabularQueryPlan(
            operation="lookup", table_id=self.table, column_ids=["B"],
            filters=[TabularFilter(column_id="A", operator="equals", value="Unit-A")],
        ))


class Generator:
    called = False

    async def generate(self, *args):
        self.called = True
        return QuestionAnswerDraft(answer="추측한 원인", evidence=[], confidence=0.9,
                                   claims=[SourceClaim(kind="unknown")])


def run(question, classifier):
    summary, index = table_fixture([(1, 1, [
        ["장비", "네트워크 안정"], ["Unit-A", "x"], ["Unit-B", "o"],
    ])], "점검")
    generator = Generator()
    service = WorkbookQuestionService(generator, create_default_tool_registry(), classifier=classifier)
    return asyncio.run(service.answer(question, summary, index)), generator


def test_successful_lookup_cannot_certify_the_meaning_of_a_symbol():
    answer, _ = run("Unit-A의 네트워크가 안정적이라는 뜻이야?", Classifier())
    assert "x" in answer.answer
    assert answer.status == "limited"
    assert answer.verification.level != "request_checked"
    assert "interpretation_unverified" in answer.verification.checks
    assert any("의미·원인" in note for note in answer.limitations)


def test_direct_literal_lookup_keeps_its_proven_request_alignment():
    answer, _ = run("Unit-A의 네트워크 안정 값은?", Classifier())
    assert answer.status == "answered"
    assert answer.verification.level == "request_checked"
    assert "interpretation_unverified" not in answer.verification.checks


def test_bad_lookup_plan_does_not_short_circuit_a_causal_question():
    answer, generator = run("왜 Unit-A의 네트워크 안정이 x야?", Classifier("Missing!A1:B3"))
    assert "집계할 시트와 열 이름" not in answer.answer
    assert answer.verification.level != "request_checked"
    assert generator.called or answer.status == "limited"
