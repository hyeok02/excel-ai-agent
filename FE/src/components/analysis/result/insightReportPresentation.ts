import type { InsightReportResult, InsightResult } from '@/api/analysis/insightTypes'

const REMOVED_CAUSE_REASON =
  '원인을 직접 입증하는 수식·메타데이터 근거가 없어 원인 문장을 제외했습니다.'

const REANALYSIS_NOTICE =
  '저장된 결과 중 원본 근거를 확인할 수 없는 내용은 숨겼습니다. 해당 파일을 다시 분석해 주세요.'

const canDisplayInsight = (insight: InsightResult) => {
  if (!insight.fact.trim() || !insight.evidence.some((item) => item.trim())) {
    return false
  }

  // 이전 검증기는 수치·근거 불일치도 LIMITED로 저장했다. 원인만 제거한
  // 경우 외에는 상태나 신뢰도만 보고 해당 내용을 사실로 다시 노출하지 않는다.
  if (insight.validationReasons.some((reason) => reason !== REMOVED_CAUSE_REASON)) {
    return false
  }
  return (
    insight.validationStatus === 'verified' ||
    (insight.validationStatus === 'limited' && insight.validationReasons.length > 0)
  )
}

/** 저장된 과거 결과에도 적용하는 표시 방어선이며, 원본 검증을 대체하지 않는다. */
export const prepareInsightReportPresentation = (source: InsightReportResult) => {
  const insights = source.insights
    .filter(canDisplayInsight)
    .map((insight) =>
      insight.validationReasons.includes(REMOVED_CAUSE_REASON)
        ? { ...insight, cause: null, impact: null, recommendation: null }
        : insight,
    )
  const suppressedCount = source.insights.length - insights.length
  const hasSuppressedInsights = suppressedCount > 0
  const verifiedCount = insights.filter(
    (insight) => insight.validationStatus === 'verified',
  ).length
  const blockedCount = (source.validation?.blockedCount ?? 0) + suppressedCount
  const notices = hasSuppressedInsights
    ? [REANALYSIS_NOTICE]
    : (source.validation?.notices ?? [])

  const report: InsightReportResult = {
    ...source,
    // 요약에도 배제된 문장이 남을 수 있으므로, 표시 가능한 사실로만 재구성한다.
    overview:
      insights
        .slice(0, 2)
        .map((insight) => insight.fact)
        .join(' ') || '원본 근거로 확인할 수 있는 인사이트가 없습니다.',
    insights,
    limitations: hasSuppressedInsights ? notices : source.limitations,
    hasIncompleteData: insights.some((insight) => insight.isIncomplete),
    validation: {
      generatedCount: Math.max(
        source.validation?.generatedCount ?? source.insights.length,
        insights.length + blockedCount,
      ),
      verifiedCount,
      limitedCount: insights.length - verifiedCount,
      blockedCount,
      notices,
    },
  }

  return { report, hasSuppressedInsights }
}
