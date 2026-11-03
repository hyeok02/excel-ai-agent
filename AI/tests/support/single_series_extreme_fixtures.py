"""Reusable offline workbook and service fixtures for series-extreme tests."""
from openpyxl import Workbook

from app.agent import create_default_tool_registry
from app.agent.query.service import WorkbookQuestionService
from tests.support.large_workbook_fixtures import parsed


class NoModelCalls:
    async def generate(self, *args):
        raise AssertionError("source-bound extreme selection must not call the model")

    async def classify(self, *args):
        raise AssertionError("source-bound extreme selection must not classify again")

    async def resolve(self, *args):
        raise AssertionError("source-bound extreme selection must not resolve context")


def asthma_source(*, internal_gap=False):
    book = Workbook()
    sheet = book.active
    sheet.title = "Childhood Asthma"
    sheet.append(["Childhood asthma prevalence", None, None, None, None])
    sheet.append(["Asthma Attack Prevalence", 2020, 2021, 2022, 2023])
    attack = ["Asthma Attack Prevalence", 0.10, 0.12, 0.20, 0.19]
    if internal_gap:
        attack[2] = "-"
    sheet.append(attack)
    sheet.append(["Current Asthma Prevalence", "-", 0.15, 0.18, 0.17])
    for row in range(3, 5):
        for column in range(2, 6):
            sheet.cell(row, column).number_format = "0.0%"
    return parsed(book, "childhood-asthma.xlsx")[:2]


def question_service():
    no_calls = NoModelCalls()
    return WorkbookQuestionService(
        no_calls, create_default_tool_registry(), classifier=no_calls, context_resolver=no_calls,
    )
