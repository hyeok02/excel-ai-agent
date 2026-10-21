import type { WorkbookQuestionAnswer } from '../../../../api/analysis/questionTypes.ts'

const REQUIRED: Record<string, string[]> = {
  scoped_derived_trend: [
    'filters',
    'grouping',
    'complete_series',
    'positive_denominator',
    'operand_lineage',
    'aligned_periods',
    'aligned_entity_scope',
  ],
  resampled_trend: [
    'complete_series',
    'calendar_buckets',
    'explicit_temporal_aggregation',
    'complete_periods',
  ],
  joined_trend: ['typed_join_keys', 'many_to_one_cardinality', 'complete_join_coverage'],
}

/** A generic lookup certificate cannot certify a composed calculation. */
export const composedQuestionVerification = (
  answer: WorkbookQuestionAnswer,
  checks: string[],
) => {
  const tools = answer.selectedTools.filter((tool) => tool in REQUIRED)
  if (
    !tools.length ||
    answer.status !== 'answered' ||
    answer.verification?.level !== 'request_checked'
  ) {
    return null
  }
  const required = [
    'table_scope',
    'source_values',
    'request_alignment',
    'calculation',
    'unit',
    ...tools.flatMap((tool) => REQUIRED[tool]),
  ]
  const derivedBasisChecked =
    !tools.includes('scoped_derived_trend') ||
    checks.includes('same_population_baseline') ||
    checks.includes('scoped_population_denominator')
  if (
    derivedBasisChecked &&
    required.every((check) => checks.includes(check)) &&
    answer.evidence.length > 0 &&
    answer.limitations.length === 0
  ) {
    return null
  }
  return {
    label: '계산 범위 확인 필요',
    tone: answer.limitations.length ? 'limited' : 'neutral',
    explanation:
      '조건·비교 기준·기간 집계 또는 표 연결의 검증 항목이 완전하지 않아 전체 계산의 확인 표시를 하지 않았습니다.',
  } as const
}
