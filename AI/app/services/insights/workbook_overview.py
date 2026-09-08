"""Create one common, source-grounded sentence describing any workbook."""
import re

from app.services.insights.claim_grounding import grounded_claim
from app.services.insights.derived_claim_grounding import grounded_derivation
from app.services.insights.models import (
    ValidatedWorkbookInsightReport,
    WorkbookInsightReport,
)
from app.services.insights.numeric_validation import unmatched_numbers
from app.services.insights.reference_matching import resolve_references
from app.services.insights.review_points import grounded_tokens, mask_known_names
from app.services.insights.unit_grounding import grounded_units
from app.services.insights.validation_index import EvidenceIndex, extract_references
from app.services.insights.workbook_lead_rules import structured_lead

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
        resolved, unmatched = resolve_references(requested, index.references)
        if unmatched or not resolved:
            continue
        source = [text for ref in resolved for text in index.reference_text.get(ref, [])]
        grounded = grounded_tokens(source)
        cited = set().union(*(index.reference_numbers.get(ref, set()) for ref in resolved))
        claim = mask_known_names(lead, grounded)
        if (not unmatched_numbers(claim, cited)
                and grounded_claim(lead, source, resolved)
                and grounded_derivation(lead, source, resolved, index.numeric_changes)
                and grounded_units(lead, source, resolved, index.numeric_changes)):
            return True
    return False


def _fallback_lead(report: ValidatedWorkbookInsightReport) -> str:
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
