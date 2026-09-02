from app.agent.execution.models import AgentExecution
from app.services.insights.models import (
    InsightValidationStatus,
    InsightValidationSummary,
    ValidatedWorkbookInsight,
    ValidatedWorkbookInsightReport,
    WorkbookInsight,
    WorkbookInsightReport,
)
from app.services.insights.numeric_validation import unmatched_numbers
from app.services.insights.reference_matching import resolve_references
from app.services.insights.review_points import grounded_review_point
from app.services.insights.validation_index import (
    EvidenceIndex,
    agent_evidence_index,
    extract_references,
    workbook_evidence_index,
)


def validate_workbook_insights(
    report: WorkbookInsightReport, context: dict[str, object]
) -> ValidatedWorkbookInsightReport:
    return _validate(report, workbook_evidence_index(context))


def validate_agent_insights(
    report: WorkbookInsightReport, execution: AgentExecution
) -> ValidatedWorkbookInsightReport:
    return _validate(report, agent_evidence_index(execution))


def _validate(
    report: WorkbookInsightReport, index: EvidenceIndex
) -> ValidatedWorkbookInsightReport:
    passed: list[ValidatedWorkbookInsight] = []
    blocked = 0
    for insight in report.insights:
        validated = _validate_insight(insight, index)
        if validated is None:
            blocked += 1
        else:
            passed.append(validated)
    limited = sum(
        item.validation_status is InsightValidationStatus.LIMITED for item in passed
    )
    verified = len(passed) - limited
    notices = []
    if blocked:
        notices.append(f"내용이나 근거가 비어 있는 인사이트 {blocked}건을 표시에서 제외했습니다.")
    if limited:
        notices.append(
            f"근거 자동 대조가 완전하지 않은 인사이트 {limited}건은 화면에 유지하고 확인 필요로 표시했습니다."
        )
    notices.extend(index.limitations)
    limitations = list(dict.fromkeys([*report.limitations, *notices]))
    overview = (
        " ".join(item.fact for item in passed[:2])
        if passed
        else "근거 검증을 통과한 인사이트가 없습니다. 원본 범위와 분석 한계를 확인하세요."
    )
    return ValidatedWorkbookInsightReport(
        overview=overview,
        insights=passed,
        limitations=limitations,
        validation=InsightValidationSummary(
            generated_count=len(report.insights),
            verified_count=verified,
            limited_count=limited,
            blocked_count=blocked,
            notices=notices,
        ),
    )


def _validate_insight(
    insight: WorkbookInsight, index: EvidenceIndex
) -> ValidatedWorkbookInsight | None:
    if not insight.fact.strip() or not insight.evidence:
        return None
    reasons: list[str] = []
    confidence_penalty = 0.0
    cited_references = [extract_references(item) for item in insight.evidence]
    if any(not items for items in cited_references):
        reasons.append("일부 근거 위치를 자동으로 해석하지 못해 원본 위치 확인이 필요합니다.")
        confidence_penalty += 0.15
    references = set().union(*cited_references)
    resolved_references, unmatched_references = resolve_references(
        references, index.references
    )
    if unmatched_references:
        reasons.append("일부 셀·범위가 분석 입력과 정확히 일치하지 않아 원본 확인이 필요합니다.")
        confidence_penalty += 0.25
    claim_text = " ".join(item for item in [insight.fact, insight.cause] if item)
    cited_numbers = set().union(
        *(
            index.reference_numbers.get(reference, set())
            for reference in resolved_references
        )
    )
    if unmatched_numbers(claim_text, cited_numbers):
        reasons.append("일부 수치 표현을 분석 입력에서 자동으로 대조하지 못했습니다.")
        confidence_penalty += 0.15
    cause = insight.cause
    if cause and not (resolved_references & index.cause_references):
        cause = None
        reasons.append("원인을 직접 입증하는 수식·메타데이터 근거가 없어 원인 문장을 제외했습니다.")
        confidence_penalty += 0.1
    status = (
        InsightValidationStatus.LIMITED
        if reasons or insight.confidence < 0.7
        else InsightValidationStatus.VERIFIED
    )
    confidence = round(max(0.0, insight.confidence - confidence_penalty), 2)
    impact = grounded_review_point(
        insight.impact, [*insight.evidence, *index.evidence_text], cited_numbers
    )
    return ValidatedWorkbookInsight(
        **insight.model_dump(exclude={"cause", "impact", "confidence"}),
        cause=cause,
        impact=impact,
        confidence=confidence,
        validation_status=status,
        validation_reasons=reasons,
    )

