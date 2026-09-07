from app.agent.execution.models import AgentExecution
from app.services.insights.claim_grounding import grounded_claim
from app.services.insights.derived_claim_grounding import grounded_derivation
from app.services.insights.unit_grounding import grounded_units
from app.services.insights.models import (
    InsightValidationStatus, ValidatedWorkbookInsight,
    ValidatedWorkbookInsightReport, WorkbookInsight, WorkbookInsightReport,
)
from app.services.insights.numeric_validation import numbers, unmatched_numbers
from app.services.insights.reference_matching import resolve_references
from app.services.insights.review_points import grounded_tokens, mask_known_names
from app.services.insights.validated_report import assemble_report, add_source_fallback
from app.services.insights.source_narratives import source_narrative_report
from app.services.insights.validation_index import (
    REFERENCE_PATTERN, EvidenceIndex, agent_evidence_index, extract_references,
    workbook_evidence_index,
)


def validate_workbook_insights(
    report: WorkbookInsightReport, context: dict[str, object]
) -> ValidatedWorkbookInsightReport:
    index = workbook_evidence_index(context)
    canonical = source_narrative_report(context)
    comparison_is_complete = any(
        isinstance(sheet, dict) and isinstance(
            sheet.get("business_facts", {}).get("comparable_transactions"), dict
        ) for sheet in context.get("sheets", [])
    )
    result = _validate(report, index, canonical.insights)
    if canonical.insights:
        baseline = _validate(canonical, index, canonical.insights)
        if len(baseline.insights) == len(canonical.insights):
            baseline.overview = canonical.overview
            baseline.validation.overview_validated = True
            _merge_model_findings(baseline, result, not comparison_is_complete)
            return baseline
    if result.insights:
        return result
    from app.services.insights.quality import build_source_report
    fallback = _validate(build_source_report(context), index)
    return add_source_fallback(result, fallback)


def validate_agent_insights(
    report: WorkbookInsightReport, execution: AgentExecution
) -> ValidatedWorkbookInsightReport:
    return _validate(report, agent_evidence_index(execution))


def _validate(report: WorkbookInsightReport, index: EvidenceIndex, canonical=()):
    passed = [item for insight in report.insights
              if (item := _validate_insight(insight, index, canonical)) is not None]
    return assemble_report(passed, len(report.insights), index.limitations)


def _validate_insight(
    insight: WorkbookInsight, index: EvidenceIndex, canonical=()
) -> ValidatedWorkbookInsight | None:
    if not insight.fact.strip() or not insight.evidence or insight.confidence < 0.7:
        return None
    cited = [extract_references(item) for item in insight.evidence]
    if any(not references for references in cited):
        return None
    references = set().union(*cited)
    resolved, unmatched = resolve_references(references, index.references)
    if unmatched or not resolved:
        return None
    source_text = [text for ref in resolved for text in index.reference_text.get(ref, [])]
    grounded = grounded_tokens(source_text)
    cited_numbers = set().union(*(index.reference_numbers.get(ref, set()) for ref in resolved))

    def supported(text: str | None) -> bool:
        if not text:
            return False
        if any(text in (item.fact, item.title) and _required_citations(item, references)
               for item in canonical):
            return True
        without_addresses = REFERENCE_PATTERN.sub(" ", text)
        claim = mask_known_names(without_addresses, grounded)
        return (
            not unmatched_numbers(claim, cited_numbers)
            and grounded_claim(text, source_text, resolved)
            and grounded_derivation(text, source_text, resolved, index.numeric_changes)
            and grounded_units(text, source_text, resolved, index.numeric_changes)
        )

    if not supported(insight.fact):
        return None
    # Do not let a valid fact carry a fabricated title, cause or recommendation.
    cause = insight.cause
    reasons = []
    if cause and (not resolved & index.cause_references or not supported(cause)):
        cause = None
        reasons.append("원인을 직접 입증하는 수식·메타데이터 근거가 없어 원인 문장을 제외했습니다.")
    status = InsightValidationStatus.LIMITED if reasons else InsightValidationStatus.VERIFIED
    return ValidatedWorkbookInsight(
        **insight.model_dump(exclude={"title", "cause", "impact", "recommendation", "evidence"}),
        title=insight.title if supported(insight.title) else "원본에서 확인한 내용",
        cause=cause,
        impact=insight.impact if supported(insight.impact) else None,
        recommendation=insight.recommendation if supported(insight.recommendation) else None,
        evidence=list(dict.fromkeys(
            match.group(0) for item in insight.evidence for match in REFERENCE_PATTERN.finditer(item)
        )),
        validation_status=status,
        validation_reasons=reasons,
    )


def _required_citations(item, references):
    required = set().union(*(extract_references(ref) for ref in item.evidence))
    return bool(required) and required <= references


def _merge_model_findings(baseline, result, include_extras=True):
    """Reserve room for independently grounded model detail without replacing the overview."""
    known_facts = {item.fact for item in baseline.insights}
    extras = [item for item in result.insights
              if include_extras and item.fact not in known_facts
              and not _duplicate(item, baseline.insights)]
    if extras:
        keep = min(len(baseline.insights), 4)
        baseline.insights = [*baseline.insights[:keep], *extras[:5 - keep]]
    verified = sum(item.validation_status is InsightValidationStatus.VERIFIED
                   for item in baseline.insights)
    baseline.validation.generated_count = len(baseline.insights) + result.validation.blocked_count
    baseline.validation.blocked_count = result.validation.blocked_count
    baseline.validation.verified_count = verified
    baseline.validation.limited_count = len(baseline.insights) - verified
    baseline.validation.notices = result.validation.notices


def _duplicate(candidate, baseline):
    candidate_refs = _item_references(candidate)
    candidate_numbers = numbers(candidate.fact)
    return bool(candidate_refs and candidate_numbers) and any(
        (candidate_refs <= _item_references(item)
         or _item_references(item) <= candidate_refs)
        and candidate_numbers == numbers(item.fact)
        for item in baseline
    )


def _item_references(item):
    return set().union(*(extract_references(ref) for ref in item.evidence))
