"""Assemble visible reports only from accepted facts, never raw LLM summaries."""
from app.services.insights.models import (
    InsightValidationStatus, InsightValidationSummary,
    ValidatedWorkbookInsightReport,
)


def assemble_report(passed, generated_count, source_limitations):
    limited = sum(item.validation_status is InsightValidationStatus.LIMITED for item in passed)
    blocked = generated_count - len(passed)
    notices = []
    if blocked:
        notices.append(f"원본 근거로 확인되지 않은 인사이트 {blocked}건을 표시에서 제외했습니다.")
    return ValidatedWorkbookInsightReport(
        overview=" ".join(item.fact for item in passed[:2]) if passed else (
            "원본 근거로 확인할 수 있는 인사이트가 없습니다. 원본 내용과 분석 범위를 확인하세요."
        ),
        insights=passed,
        # Raw model limitations can contain the same unsupported claims as facts.
        limitations=list(dict.fromkeys([*source_limitations, *notices])),
        validation=InsightValidationSummary(
            generated_count=generated_count, verified_count=len(passed) - limited,
            limited_count=limited, blocked_count=blocked, notices=notices,
        ),
    )


def add_source_fallback(result, fallback):
    if not fallback.insights:
        return result
    notice = "생성된 해석 대신 원본 셀에서 직접 확인한 내용을 표시합니다."
    fallback.validation.generated_count += result.validation.generated_count
    fallback.validation.blocked_count += result.validation.blocked_count
    fallback.validation.notices = [*result.validation.notices, notice]
    fallback.limitations = list(dict.fromkeys([
        *result.limitations, *fallback.limitations, notice,
    ]))
    return fallback
