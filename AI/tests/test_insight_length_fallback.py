import asyncio
from datetime import datetime
from io import BytesIO

from openpyxl import Workbook

from app.services.insights.generator import LangChainInsightGenerator
from app.services.workbook_parser import parse_workbook
from tests.support.narrative_contexts import trend_context


class LengthLimitedModel:
    async def ainvoke(self, _messages):
        raise RuntimeError("optional model prose failed")


def test_completion_length_uses_verified_source_narrative_instead_of_failing(monkeypatch):
    workbook = Workbook()
    sheet = workbook.active
    for row, values in enumerate([
        ["기준일", "전체 인원"],
        [datetime(2025, 1, 1), 100],
        [datetime(2025, 2, 1), 90],
    ], start=1):
        for column, value in enumerate(values, start=1):
            sheet.cell(row, column, value)
    stream = BytesIO()
    workbook.save(stream)
    workbook.close()
    summary = parse_workbook("bounded.xlsx", stream.getvalue())
    generator = LangChainInsightGenerator("unused", 10, "minimal")
    monkeypatch.setattr(generator, "_build_model", lambda _profile: LengthLimitedModel())
    monkeypatch.setattr(
        "app.services.insights.generator.build_workbook_context",
        lambda _summary, _profile: trend_context(),
    )

    report = asyncio.run(generator.generate(summary))

    assert report.insights
    assert "전체 인원" in report.overview
    assert "100" in report.overview and "90" in report.overview
