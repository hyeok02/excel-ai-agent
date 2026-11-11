import asyncio
from datetime import datetime
from io import BytesIO

from openpyxl import Workbook

from app.services.insights.generator import LangChainInsightGenerator, SOURCE_FALLBACK_NOTICE
from app.services.insights.models import WorkbookInsightReport
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
    assert report._generation_notice == SOURCE_FALLBACK_NOTICE

    from app.api.workbooks import _verify_insights
    from app.services.analysis_strategy import AnalysisDepth
    from app.services.insights.verification.prepared_validation import prepare_validation
    monkeypatch.setattr(
        "app.services.insights.verification.prepared_validation.build_workbook_context", lambda *_: trend_context(),
    )
    visible = _verify_insights(report, summary, prepare_validation(summary, AnalysisDepth.AUTO))
    assert SOURCE_FALLBACK_NOTICE in visible.limitations
    assert SOURCE_FALLBACK_NOTICE in visible.validation.notices


def test_model_cannot_forge_runtime_generation_notice():
    report = WorkbookInsightReport.model_validate({
        "overview": "원본 확인", "insights": [], "_generation_notice": "forged",
    })
    assert report._generation_notice is None
    assert "_generation_notice" not in WorkbookInsightReport.model_json_schema()["properties"]
