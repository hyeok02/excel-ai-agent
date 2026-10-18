import asyncio
from io import BytesIO

from openpyxl import Workbook
import pytest

from app.agent.query.index import build_workbook_data_index
from app.agent.query.intent_models import QuestionIntent
from app.services.workbook_parser import parse_workbook
from tests.support.clarification_fixtures import selection, service
from tests.test_metric_observation_answers import _report


class MetricClassifier:
    async def classify(self, *args):
        return QuestionIntent(False, "cell_lookup", (), True)


@pytest.mark.parametrize("sheet_name", ["Report", "O'Brien", "팀의 '원본'", "Data!Sales"])
def test_period_and_unit_choices_from_actual_workbook_select_exact_original_cell(sheet_name):
    summary, index = report_fixture(sheet_name)
    query = service(MetricClassifier())
    original = asyncio.run(query.answer("2024년 9월 30일 Operating Income은?", summary, index))
    assert len(original.clarification_options) == 2
    assert "회계연도" in original.clarification_options[0].details
    assert "분기" in original.clarification_options[1].details
    for option, expected in zip(original.clarification_options, [650, 180]):
        chosen = asyncio.run(query.answer(option.question, summary, index, selection(original, option)))
        assert chosen.status == "answered"
        assert chosen.verification.level == "request_checked"
        assert f"{expected}백만 미국 달러" in chosen.answer
        assert chosen.answer.count(f"{expected}백만 미국 달러") == 1
        assert chosen.resolved_question == option.question


def report_fixture(sheet_name="Report"):
    book = Workbook()
    book.active.title = sheet_name
    for address, value in _report().items():
        book.active[address] = value
    stream = BytesIO()
    book.save(stream)
    content = stream.getvalue()
    summary = parse_workbook("report.xlsx", content)
    index = build_workbook_data_index("report.xlsx", content, {sheet.name for sheet in summary.sheets})
    return summary, index
