"""An unproven calculation plan is answered by a checked draft, never by an unchecked number."""
import asyncio

from app.agent import create_default_tool_registry
from app.agent.query.intent_models import QuestionIntent
from app.agent.query.models import QuestionAnswerDraft
from app.agent.query.service import WorkbookQuestionService
from app.agent.query.tabular_catalog import build_query_tables
from app.agent.query.tabular_query_models import TabularQueryPlan
from app.agent.query.tabular_routing import UNPROVEN_NOTE
from tests.tabular_query_fixtures import table_fixture

ROWS = [["Account", "Territory", "Net Amount"], ["Orion", "North", 17], ["Vega", "South", 90], ["Lyra", "North", 33]]


class Draft:
    def __init__(self, answer, evidence):
        self.answer, self.evidence, self.calls = answer, evidence, 0

    async def generate(self, *args):
        self.calls += 1
        return QuestionAnswerDraft(answer=self.answer, confidence=0.9, evidence=self.evidence)


class Unproven:
    """A plan the validators reject: a list ordered by amount for a question about one account."""

    def __init__(self, table):
        self.plan = TabularQueryPlan(operation="row_list", table_id=table.id, column_ids=["A"], order_by="C", limit=1)

    async def classify(self, *args):
        return QuestionIntent(False, "row_list", (), True, self.plan)


def _ask(draft, question="Vega의 Net Amount는 얼마야?"):
    summary, index = table_fixture([(1, 1, ROWS)])
    service = WorkbookQuestionService(draft, create_default_tool_registry(),
                                      classifier=Unproven(build_query_tables(summary)[0]))
    return asyncio.run(service.answer(question, summary, index))


def test_a_draft_quoting_source_cells_is_shown_with_the_unproven_plan_note() -> None:
    cells = ["Arbitrary!A3", "Arbitrary!B3", "Arbitrary!C3", "Arbitrary!B1", "Arbitrary!C1"]
    draft = Draft("Vega의 Net Amount는 90입니다.", cells)
    answer = _ask(draft)

    assert draft.calls == 1 and "90" in answer.answer
    assert answer.status == "limited" and UNPROVEN_NOTE in answer.limitations
    assert answer.verification.level != "request_checked"


def test_a_fabricated_number_is_never_shown() -> None:
    draft = Draft("Vega의 Net Amount는 987654321입니다.", ["Arbitrary!C3"])
    answer = _ask(draft)

    assert draft.calls == 1 and "987654321" not in answer.answer
    assert answer.verification.level != "request_checked"
