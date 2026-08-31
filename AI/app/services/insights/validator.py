from app.agent.execution.models import AgentExecution
from app.services.insights.models import (
    InsightValidationStatus,
    InsightValidationSummary,
    ValidatedWorkbookInsight,
    ValidatedWorkbookInsightReport,
    WorkbookInsight,
    WorkbookInsightReport,
)
from app.services.insights.validation_index import (
    EvidenceIndex,
    agent_evidence_index,
    extract_references,
    numbers,
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
    if not insight.fact.strip() or not insight.impact.strip() or not insight.evidence:
        return None
    reasons: list[str] = []
    cited_references = [extract_references(item) for item in insight.evidence]
    if any(not items for items in cited_references):
        reasons.append("일부 근거 위치를 자동으로 해석하지 못해 원본 위치 확인이 필요합니다.")
    references = set().union(*cited_references)
    if references - index.references:
        reasons.append("일부 셀·범위가 분석 입력과 정확히 일치하지 않아 원본 확인이 필요합니다.")
    claim_text = " ".join(
        item for item in [insight.fact, insight.cause, insight.impact] if item
    )
    if numbers(claim_text) - index.numbers:
        reasons.append("일부 수치 표현을 분석 입력에서 자동으로 대조하지 못했습니다.")
    cause = insight.cause
    if cause and not any(item in index.cause_references for item in references):
        cause = None
        reasons.append("원인을 직접 입증하는 수식·메타데이터 근거가 없어 원인 문장을 제외했습니다.")
    status = (
        InsightValidationStatus.LIMITED
        if reasons or insight.confidence < 0.7
        else InsightValidationStatus.VERIFIED
    )
    confidence = min(insight.confidence, 0.79) if reasons else insight.confidence
    return ValidatedWorkbookInsight(
        **insight.model_dump(exclude={"cause", "confidence"}),
        cause=cause,
        confidence=confidence,
        validation_status=status,
        validation_reasons=reasons,
    )
