import assert from 'node:assert/strict'
import test from 'node:test'

import { questionVerificationPresentation } from '../src/components/analysis/result/questions/questionVerification.ts'
import { questionAnswer } from './questionContext.fixtures.ts'

test('a successful lookup cannot certify unproven business meaning with a green badge', () => {
  const result = questionVerificationPresentation(
    questionAnswer({
      verification: {
        level: 'request_checked',
        checks: [
          'table_scope',
          'source_values',
          'request_alignment',
          'interpretation_unverified',
        ],
      },
    }),
  )
  assert.equal(result.label, '원본 확인 · 의미 미확인')
  assert.equal(result.tone, 'limited')
  assert.match(result.explanation, /업무상 의미나 원인까지 입증한 것은 아닙니다/)
})

test('unverified interpretations never claim original values were checked', () => {
  for (const status of ['answered', 'limited', 'insufficient_evidence'] as const) {
    const result = questionVerificationPresentation(
      questionAnswer({
        status,
        verification: { level: 'unverified', checks: ['interpretation_unverified'] },
      }),
    )
    assert.equal(result.label, '의미 확인 필요')
    assert.equal(result.tone, 'neutral')
  }
})

test('context, formula and header caution remain explicit when interpretation is unknown', () => {
  for (const [checks, label] of [
    [['context_resolved'], '맥락 연결 · 원본 확인'],
    [['bounded_recalculation'], '수식 재계산'],
    [['cited_cells', 'header_labels', 'header_positions'], '항목 구조 확인'],
  ] as const) {
    const result = questionVerificationPresentation(
      questionAnswer({
        verification: {
          level: 'source_checked',
          checks: [...checks, 'interpretation_unverified'],
        },
      }),
    )
    assert.equal(result.label, label)
    assert.equal(result.tone, 'limited')
  }
})
