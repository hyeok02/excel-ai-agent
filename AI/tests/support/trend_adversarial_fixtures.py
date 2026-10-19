"""Offline synthetic trend sources, independent of uploaded business workbooks."""
import asyncio

from app.agent import create_default_tool_registry
from app.agent.query.service import WorkbookQuestionService
from app.agent.query.tabular_catalog import build_query_tables
from app.agent.query.tabular_query_models import TabularQueryPlan
from tests.support.large_workbook_fixtures import FixedClassifier, NoGeneratedAnswer
from tests.tabular_query_fixtures import table_fixture

QUESTION = "전체 직원 수의 기간별 추이를 설명해줘"
DATES = ["2024-03-31", "2024-06-30", "2024-09-30", "2024-12-31"]


def source(values=(100, 150, 120, 130), *, order=None, header="Total Employees"):
    rows = [[date, value, 9000 + number] for number, (date, value) in enumerate(zip(DATES, values))]
    if order is not None:
        rows = [rows[number] for number in order]
    return table_fixture([(1, 1, [["Date", header, "Revenue"], *rows])])


def direct(summary, index, question=QUESTION):
    from app.agent.query.trend_answers import trend_answer
    return trend_answer(question, summary, index)


def checked(answer):
    assert answer is not None
    assert answer.status == "answered", answer.model_dump()
    assert answer.verification.level == "request_checked", answer.model_dump()


def not_certified(answer):
    assert answer is None or answer.verification.level != "request_checked", answer.model_dump()


def wrong_aggregation(summary, index, question=QUESTION):
    table = build_query_tables(summary)[0]
    plan = TabularQueryPlan(operation="numeric_summary", table_id=table.id,
                            column_ids=["C"], statistic="sum")
    service = WorkbookQuestionService(NoGeneratedAnswer(), create_default_tool_registry(),
                                      classifier=FixedClassifier(plan))
    return asyncio.run(service.answer(question, summary, index))
