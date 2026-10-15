import assert from 'node:assert/strict'
import test from 'node:test'

import { questionVerificationPresentation } from '../src/components/analysis/result/questions/questionVerification.ts'
import { questionAnswer } from './questionContext.fixtures.ts'

const checks = ['cited_cells', 'source_values', 'claim_bindings', 'claim_semantics']

test('claim source bindings explain their scope without certifying all business interpretations', () => {
  const result = questionVerificationPresentation(
    questionAnswer({
      status: 'limited',
      verification: { level: 'source_checked', checks },
    }),
  )
  assert.equal(result.label, '주장별 원본 대조')
  assert.equal(result.tone, 'limited')
  assert.match(result.explanation, /값·대상·기간·항목/)
  assert.match(result.explanation, /업무상 의미나 원인까지 입증한 것은 아닙니다/)
})

test('fully source-backed prose claims still do not imply request-wide green verification', () => {
  const result = questionVerificationPresentation(
    questionAnswer({
      status: 'answered',
      verification: { level: 'source_checked', checks },
    }),
  )
  assert.equal(result.label, '주장별 원본 대조')
  assert.equal(result.tone, 'neutral')
})

test('claim label requires value and binding checks and never overrides context uncertainty', () => {
  const incomplete = questionVerificationPresentation(
    questionAnswer({
      verification: { level: 'source_checked', checks: ['claim_semantics'] },
    }),
  )
  assert.notEqual(incomplete.label, '주장별 원본 대조')
  const contextual = questionVerificationPresentation(
    questionAnswer({
      verification: { level: 'source_checked', checks: [...checks, 'context_resolved'] },
    }),
  )
  assert.equal(contextual.label, '맥락 연결 · 원본 확인')
  assert.equal(contextual.tone, 'limited')
})
