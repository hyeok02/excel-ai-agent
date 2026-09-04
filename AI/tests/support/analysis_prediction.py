from __future__ import annotations

from app.agent.query import build_workbook_data_index
from app.agent.query.question_validation import vague_question_answer
from app.services.insights.context import build_workbook_context
from app.services.insights.models import WorkbookInsight, WorkbookInsightReport
from app.services.insights.quality import metric_changes, subject_name
from app.services.insights.validator import validate_workbook_insights
from app.services.workbook_parser import parse_workbook
from tests.support.analysis_regression_models import (
    CLARIFY,
    DROP,
    KEEP,
    SPECIFIC,
    AnalysisFixtureCase,
    AnalysisPrediction,
    MetricChange,
)


class WorkbookAnalysisPredictor:
    """픽스처 워크북을 실제 분석 경로로 통과시켜 결정론 판정을 만든다.

    OpenAI를 호출하지 않는다. LLM이 낼 법한 문장을 미리 넣어 두고, 그 문장을
    검증기가 남기는지 버리는지만 본다.
    """

    def predict(self, case: AnalysisFixtureCase) -> AnalysisPrediction:
        content = case.workbook_path.read_bytes()
        summary = parse_workbook(case.workbook_path.name, content)
        context = build_workbook_context(summary)
        return AnalysisPrediction(
            workbook=case.name,
            subject=subject_name(context),
            changes=tuple(
                MetricChange.from_mapping(item) for item in metric_changes(context)
            ),
            review_points=_review_verdicts(context, case.review_point_texts),
            questions=_question_verdicts(summary, content, case.question_texts),
        )


def review_point_verdict(context: dict[str, object], text: str) -> str:
    """검토 포인트 한 문장이 근거 대조를 통과하는지 판정한다."""
    report = _probe_report(text, _source_references(context))
    result = validate_workbook_insights(report, context)
    kept = result.insights[0].impact if result.insights else None
    return KEEP if kept else DROP


def _review_verdicts(
    context: dict[str, object], texts: tuple[str, ...]
) -> dict[str, str]:
    return {text: review_point_verdict(context, text) for text in texts}


def _question_verdicts(
    summary: object, content: bytes, texts: tuple[str, ...]
) -> dict[str, str]:
    index = build_workbook_data_index(
        summary.filename, content, {sheet.name for sheet in summary.sheets}
    )
    return {
        text: CLARIFY if vague_question_answer(text, index) else SPECIFIC
        for text in texts
    }


def _source_references(context: dict[str, object]) -> list[str]:
    # The probe reviews selected data, not arbitrary A1. Cite the actual rows
    # so the same scoped source gate as production can evaluate its vocabulary.
    return list(dict.fromkeys(
        str(record["location"])
        for sheet in context.get("sheets", [])
        for record in sheet.get("business_facts", {}).get("selected_records", [])
        if record.get("location")
    )) or ["Sheet1!A1"]


def _probe_report(impact: str, references: list[str]) -> WorkbookInsightReport:
    return WorkbookInsightReport(
        overview="검토 포인트 판정용 입력",
        insights=[
            WorkbookInsight(
                title="검토 포인트 판정",
                fact="표 구성을 확인했습니다.",
                cause=None,
                impact=impact,
                category="summary",
                severity="info",
                evidence=references,
                recommendation=None,
                confidence=0.9,
            )
        ],
    )
