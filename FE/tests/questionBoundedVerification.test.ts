import assert from 'node:assert/strict'
import test from 'node:test'

import { questionVerificationPresentation } from '../src/components/analysis/result/questions/questionVerification.ts'
import { questionAnswer } from './questionContext.fixtures.ts'

for (const check of [
  'semantic_alias_resolved',
  'premise_not_confirmed',
  'category_match_interpreted',
  'rank_interpretation',
]) {
  test(`${check} cannot become green even with stale request-wide metadata`, () => {
    const answer = questionAnswer({
      verification: {
        level: 'request_checked',
        checks: ['table_scope', 'metric', 'source_cells', check],
      },
    })
    assert.equal(questionVerificationPresentation(answer).tone, 'limited')
    answer.verification!.level = 'unverified'
    assert.equal(questionVerificationPresentation(answer).tone, 'neutral')
    answer.status = 'insufficient_evidence'
    assert.equal(questionVerificationPresentation(answer).tone, 'neutral')
  })
}

test('interpreted rank explains both the source name and aggregation basis in amber', () => {
  const result = questionVerificationPresentation(
    questionAnswer({
      status: 'limited',
      verification: {
        level: 'source_checked',
        checks: [
          'source_values',
          'relative_group_rank',
          'semantic_alias_resolved',
          'rank_interpretation',
        ],
      },
    }),
  )
  assert.equal(result.label, '해석 후 원본 대조')
  assert.equal(result.tone, 'limited')
  assert.match(result.explanation, /대상명과 순위 기준/)
  assert.match(result.explanation, /집계 항목·방식/)
  assert.match(result.explanation, /해석한 질문이 의도와 맞는지/)
})

test('interpreted rank cannot inherit a green compound badge from stale metadata', () => {
  const base = questionAnswer()
  const result = questionVerificationPresentation(
    questionAnswer({
      selectedTools: ['composite_question'],
      evidence: [1, 2].map((part) => ({
        ...base.evidence[0],
        label: `문항 ${part} · 원본`,
      })),
      verification: {
        level: 'request_checked',
        checks: [
          'compound_parts_2',
          'compound_request_coverage',
          'independent_subquestions',
          'request_alignment',
          'rank_interpretation',
        ],
      },
    }),
  )
  assert.equal(result.label, '해석 후 원본 대조')
  assert.equal(result.tone, 'limited')
})

test('unverified interpreted ranks never claim that source comparison completed', () => {
  const result = questionVerificationPresentation(
    questionAnswer({
      verification: { level: 'unverified', checks: ['rank_interpretation'] },
    }),
  )
  assert.equal(result.label, '순위 해석 확인 필요')
  assert.equal(result.tone, 'neutral')
  assert.match(result.explanation, /원본 대조를 완료하지 못했습니다/)
})
