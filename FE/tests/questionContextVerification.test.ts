import assert from 'node:assert/strict'
import test from 'node:test'

import { questionVerificationPresentation } from '../src/components/analysis/result/questions/questionVerification.ts'
import { questionAnswer } from './questionContext.fixtures.ts'

test('ambiguous conversation context asks for its target instead of reporting verification failure', () => {
  const result = questionVerificationPresentation(
    questionAnswer({
      status: 'insufficient_evidence',
      selectedTools: ['clarify_question_context'],
    }),
  )
  assert.equal(result.label, '질문 맥락 확인 필요')
  assert.equal(result.tone, 'neutral')
  assert.match(result.explanation, /어떤 항목이나 앞선 질문/)
})

test('resolved context shows a limited source check and asks the user to confirm interpretation', () => {
  const result = questionVerificationPresentation(
    questionAnswer({
      status: 'limited',
      resolvedQuestion: '매출의 최대값은?',
      verification: {
        level: 'source_checked',
        checks: ['context_resolved', 'source_values'],
      },
    }),
  )
  assert.equal(result.label, '맥락 연결 · 원본 확인')
  assert.equal(result.tone, 'limited')
  assert.match(result.explanation, /원본 값을 다시 확인/)
  assert.match(result.explanation, /의도한 대상/)
})

test('resolved model context can never turn stale request checks into a green badge', () => {
  const result = questionVerificationPresentation(
    questionAnswer({
      verification: {
        level: 'request_checked',
        checks: ['context_resolved', 'table_scope', 'source_values', 'request_alignment'],
      },
    }),
  )
  assert.equal(result.tone, 'limited')
})

test('resolving context alone never claims original values have been checked', () => {
  const result = questionVerificationPresentation(
    questionAnswer({
      verification: { level: 'unverified', checks: ['context_resolved'] },
    }),
  )
  assert.equal(result.label, '맥락 연결 · 근거 확인 필요')
  assert.equal(result.tone, 'neutral')
})

test('formula recomputation and header placement restrictions remain explicit after context resolution', () => {
  for (const [checks, label] of [
    [['context_resolved', 'bounded_recalculation'], '수식 재계산'],
    [
      ['context_resolved', 'cited_cells', 'header_labels', 'header_positions'],
      '항목 구조 확인',
    ],
  ] as const) {
    const result = questionVerificationPresentation(
      questionAnswer({
        status: 'limited',
        verification: { level: 'source_checked', checks: [...checks] },
      }),
    )
    assert.equal(result.label, label)
    assert.equal(result.tone, 'limited')
  }
})
