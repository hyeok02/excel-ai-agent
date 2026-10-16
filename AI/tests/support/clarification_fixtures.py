import asyncio

from app.agent import create_default_tool_registry
from app.agent.query.conversation_models import QuestionConversation
from app.agent.query.intent_models import QuestionIntent
from app.agent.query.service import WorkbookQuestionService
from app.agent.query.tabular_catalog import build_query_tables
from app.agent.query.tabular_query_models import TabularQueryPlan
from tests.tabular_query_fixtures import table_fixture


class ForbiddenModelCall(BaseException):
    """Not swallowed by production fallback handlers that catch Exception."""


class NeverModel:
    async def generate(self, *args):
        raise ForbiddenModelCall("No generated answer is allowed in source-choice tests")

    async def classify(self, *args):
        raise ForbiddenModelCall("Invalid selections must not classify")

    async def resolve(self, *args):
        raise ForbiddenModelCall("Source choices must not need a context model")


class QueryClassifier:
    def __init__(self, table, column="C", statistic="sum", filters=()):
        self.table, self.column, self.statistic, self.questions = table, column, statistic, []
        self.filters = filters

    async def classify(self, question, summary):
        self.questions.append(question)
        plan = TabularQueryPlan(operation="numeric_summary", table_id=self.table.id,
                                column_ids=[self.column], statistic=self.statistic, filters=list(self.filters))
        return QuestionIntent(False, "aggregation", (), True, plan)


def fixture(sheet_name="North America"):
    return table_fixture([(1, 1, [
        ["Record", "Revenue (USD) (2025)", "Revenue (EUR) (2025)"],
        ["One", 10, 100], ["Two", 20, 200],
    ])], sheet_name)


def service(classifier=None, resolver=None):
    return WorkbookQuestionService(NeverModel(), create_default_tool_registry(),
                                    classifier=classifier or NeverModel(), context_resolver=resolver or NeverModel())


def initial(summary, index, question="Revenue 합계는?"):
    classifier = QueryClassifier(build_query_tables(summary)[0])
    return asyncio.run(service(classifier).answer(question, summary, index))


def selection(answer, option):
    return QuestionConversation(selection={
        "source_question": answer.resolved_question or answer.question, "option_id": option.id,
    })
