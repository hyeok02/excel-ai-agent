import assert from 'node:assert/strict'
import test from 'node:test'

import type { WorkbookQuestionAnswer } from '../src/api/analysis/questionTypes.ts'
import { questionVerificationPresentation } from '../src/components/analysis/result/questions/questionVerification.ts'

const common = [
  'table_scope',
  'source_values',
  'request_alignment',
  'calculation',
  'unit',
]
const proofs: Record<string, string[]> = {
  scoped_derived_trend: [
    'filters',
    'grouping',
    'complete_series',
    'positive_denominator',
    'operand_lineage',
    'aligned_periods',
    'aligned_entity_scope',
    'same_population_baseline',
  ],
  resampled_trend: [
    'complete_series',
    'calendar_buckets',
    'explicit_temporal_aggregation',
    'complete_periods',
  ],
  joined_trend: ['typed_join_keys', 'many_to_one_cardinality', 'complete_join_coverage'],
}

const answer = (tools: string[], checks: string[]): WorkbookQuestionAnswer => ({
  question: '조건별 기간 추이를 비교해줘',
  answer: '원본에서 계산한 결과',
  status: 'answered',
  confidence: 1,
  selectedTools: tools,
  evidence: [
    {
      kind: 'cell',
      sheetName: 'Data',
      reference: 'B2',
      description: '원본',
      value: 100,
      formula: null,
      label: '인원',
    },
  ],
  limitations: [],
  verification: { level: 'request_checked', checks },
})

for (const [tool, required] of Object.entries(proofs)) {
  test(`${tool} needs every operation-specific proof before green verification`, () => {
    const all = [...common, ...required]
    assert.equal(questionVerificationPresentation(answer([tool], all)).tone, 'verified')
    for (const missing of all) {
      assert.notEqual(
        questionVerificationPresentation(
          answer(
            [tool],
            all.filter((check) => check !== missing),
          ),
        ).tone,
        'verified',
        missing,
      )
    }
  })
}

test('a joined derived result must prove both operations', () => {
  const tools = ['joined_trend', 'scoped_derived_trend']
  const checks = [...common, ...proofs.joined_trend, ...proofs.scoped_derived_trend]
  assert.equal(questionVerificationPresentation(answer(tools, checks)).tone, 'verified')
  assert.notEqual(
    questionVerificationPresentation(answer(tools, [...common, ...proofs.joined_trend]))
      .tone,
    'verified',
  )
  const share = checks.filter((check) => check !== 'same_population_baseline')
  share.push('scoped_population_denominator')
  assert.equal(questionVerificationPresentation(answer(tools, share)).tone, 'verified')
})

test('incomplete periods, missing evidence and limitations cannot become green', () => {
  const value = answer(['resampled_trend'], [...common, ...proofs.resampled_trend])
  assert.notEqual(
    questionVerificationPresentation({ ...value, evidence: [] }).tone,
    'verified',
  )
  assert.notEqual(
    questionVerificationPresentation({ ...value, limitations: ['전체 기간 미확인'] })
      .tone,
    'verified',
  )
  assert.notEqual(
    questionVerificationPresentation({ ...value, status: 'limited' }).tone,
    'verified',
  )
})
