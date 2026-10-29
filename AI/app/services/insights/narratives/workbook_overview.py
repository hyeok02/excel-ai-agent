"""Create one common, source-grounded sentence describing any workbook."""
import re

from app.services.insights.verification.statement_grounding import grounded_statement
from app.services.insights.models import (
    ValidatedWorkbookInsightReport,
    WorkbookInsightReport,
)
from app.services.insights.verification.reference_matching import resolve_references
from app.services.insights.verification.validation_index import EvidenceIndex, extract_references
from app.services.insights.narratives.workbook_lead_rules import structured_lead

CONTEXT_SENTENCE = re.compile(
    r"^\s*(이 파일은\s+.+?(?:자료입니다|다룹니다|보여줍니다)\.)", re.S,
)


def add_workbook_context(
    draft: WorkbookInsightReport,
    report: ValidatedWorkbookInsightReport,
    context: dict[str, object],
    index: EvidenceIndex,
) -> ValidatedWorkbookInsightReport:
    """Prepend the context only after the supporting insights are validated."""
    if not report.insights:
        return report
    existing = _lead_from(report.overview)
    generated = _lead_from(draft.overview)
    lead = (
        structured_lead(context, report)
        or (existing if _supported(existing, report, index) else "")
        or (generated if _supported(generated, report, index) else "")
        or _fallback_lead(report)
    )
    details = report.overview.strip()
    if existing:
        details = details[len(existing):].strip()
    return report.model_copy(update={"overview": f"{lead} {details}".strip()})


def _lead_from(overview: str) -> str:
    match = CONTEXT_SENTENCE.match(overview or "")
    return " ".join(match.group(1).split()) if match else ""


def _supported(
    lead: str,
    report: ValidatedWorkbookInsightReport,
    index: EvidenceIndex,
) -> bool:
    if not lead or len(lead) > 180:
        return False
    for item in report.insights:
        requested = set().union(*(extract_references(ref) for ref in item.evidence))
        resolved, unmatched = resolve_references(
            requested, index.reference_index if index.reference_index is not None else index.references
        )
        if unmatched or not resolved:
            continue
        if grounded_statement(lead, index, resolved):
            return True
    return False


def _fallback_lead(report: ValidatedWorkbookInsightReport) -> str:
    if report.insights and all(item.fact.startswith("확인된 내용은 ")
                               for item in report.insights):
        return "이 파일은 원본 표의 항목별 기록을 정리한 자료입니다."
    topics = []
    for item in report.insights[:2]:
        topic = " ".join(item.title.split()).strip(" .")
        if topic == "원본에서 확인한 내용" or not topic or len(topic) > 60:
            continue
        if topic.casefold() not in {value.casefold() for value in topics}:
            topics.append(topic)
    if not topics:
        return "이 파일은 원본에서 확인된 주요 내용을 정리한 자료입니다."
    return f"이 파일은 {'와 '.join(topics)} 관련 내용을 정리한 자료입니다."
