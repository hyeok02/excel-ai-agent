import assert from 'node:assert/strict'
import test from 'node:test'

import { questionVerificationPresentation } from '../src/components/analysis/result/questions/questionVerification.ts'
import { questionAnswer } from './questionContext.fixtures.ts'

const baseChecks = ['table_scope', 'source_values', 'request_alignment', 'calculation']
const verified = (tools: string[] = ['tabular_query'], extraChecks: string[] = []) =>
  questionAnswer({
    selectedTools: tools,
    verification: { level: 'request_checked', checks: [...baseChecks, ...extraChecks] },
  })

test('a complete original-source calculation retains its green badge', () => {
  assert.equal(questionVerificationPresentation(verified()).tone, 'verified')
})

test('stale request metadata cannot certify a result without original evidence', () => {
  const value = verified()
  for (const evidence of [
    [],
    [{ ...value.evidence[0], sheetName: '' }],
    [{ ...value.evidence[0], reference: '' }],
    [{ ...value.evidence[0], reference: 'computed result' }],
    [{ ...value.evidence[0], kind: 'metadata' }],
  ]) {
    assert.notEqual(
      questionVerificationPresentation({ ...value, evidence }).tone,
      'verified',
    )
  }
})

test('an answered result with remaining limitations never becomes fully verified', () => {
  const result = questionVerificationPresentation({
    ...verified(),
    limitations: ['전체 행을 확인하지 못했습니다.'],
  })
  assert.equal(result.tone, 'limited')
})

test('source ranges and blank or zero values remain valid evidence for verified lookups', () => {
  const value = verified()
  for (const sourceValue of [0, false, null, '']) {
    const evidence = [
      { ...value.evidence[0], kind: 'range', reference: '$A$1:$C$9', value: sourceValue },
    ]
    assert.equal(
      questionVerificationPresentation({ ...value, evidence }).tone,
      'verified',
    )
  }
})

const operationChecks: Record<string, string[]> = {
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

for (const [tool, required] of Object.entries(operationChecks)) {
  test(`${tool} cannot use generic lookup checks to conceal missing calculation proofs`, () => {
    const value = verified([tool], required)
    assert.equal(questionVerificationPresentation(value).tone, 'verified')
    for (const missing of required) {
      const verification = {
        level: 'request_checked' as const,
        checks: value.verification!.checks.filter((check) => check !== missing),
      }
      assert.notEqual(
        questionVerificationPresentation({ ...value, verification }).tone,
        'verified',
        missing,
      )
    }
  })
}
