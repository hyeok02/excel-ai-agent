import type { WorkbookQuestionAnswer } from '../../../../api/analysis/questionTypes.ts'

const OPERATION_CHECKS: Record<string, string[]> = {
  tabular_query: ['calculation'],
  chronological_trend: ['calculation', 'complete_series', 'chronological_order'],
  grouped_trend: ['calculation', 'complete_series', 'filters', 'grouping'],
  compare_trend_series: [
    'calculation',
    'complete_series',
    'all_requested_metrics',
    'aligned_periods',
    'aligned_units',
    'aligned_entity_scope',
  ],
  derived_trend: [
    'calculation',
    'complete_series',
    'positive_denominator',
    'operand_lineage',
    'aligned_periods',
    'aligned_entity_scope',
  ],
  grouped_share_trend: [
    'calculation',
    'complete_category_grid',
    'no_subtotal_double_count',
  ],
}

const SOURCE_RANGE = /^\$?[A-Z]{1,3}\$?[1-9]\d*(?::\$?[A-Z]{1,3}\$?[1-9]\d*)?$/i

/** Old or contradictory verification metadata cannot certify a complete answer. */
export const requestQuestionVerification = (
  answer: WorkbookQuestionAnswer,
  checks: string[],
) => {
  if (answer.status !== 'answered' || answer.verification?.level !== 'request_checked') {
    return null
  }
  const hasOriginalEvidence = answer.evidence.some(
    (item) =>
      ['cell', 'range', 'formula'].includes(item.kind) &&
      item.sheetName.trim().length > 0 &&
      SOURCE_RANGE.test(item.reference),
  )
  const required = answer.selectedTools.flatMap((tool) => OPERATION_CHECKS[tool] ?? [])
  if (
    hasOriginalEvidence &&
    answer.limitations.length === 0 &&
    required.every((check) => checks.includes(check))
  )
    return null
  return {
    label: answer.limitations.length ? '일부 범위만 대조' : '검증 근거 확인 필요',
    tone: answer.limitations.length ? 'limited' : 'neutral',
    explanation:
      '원본 위치·계산 검증 항목 또는 확인 한계가 남아 있어 전체 답변의 확인 표시를 하지 않았습니다.',
  } as const
}
