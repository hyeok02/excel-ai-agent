import assert from 'node:assert/strict'
import test from 'node:test'

import type { WorkbookQuestionAnswer } from '../src/api/analysis/questionTypes.ts'
import { questionVerificationPresentation } from '../src/components/analysis/result/questions/questionVerification.ts'

const answer = (
  overrides: Partial<WorkbookQuestionAnswer> = {},
): WorkbookQuestionAnswer => ({
  question: '조건에 맞는 행의 합계는?',
  answer: '100',
  status: 'answered',
  confidence: 1,
  selectedTools: ['search_workbook_data'],
  evidence: [],
  limitations: [],
  ...overrides,
})

test('answered status and high confidence alone never show a verified badge', () => {
  assert.equal(questionVerificationPresentation(answer()).tone, 'neutral')
})

test('matching cited cells does not certify the requested scope or calculation', () => {
  const result = questionVerificationPresentation(
    answer({
      verification: { level: 'source_checked', checks: ['cited_cells'] },
    }),
  )
  assert.equal(result.tone, 'neutral')
  assert.match(result.explanation, /범위 전체를 검증한 것은 아닙니다/)
})

test('only explicit request checks on a complete result show the green badge', () => {
  const verification = {
    level: 'request_checked',
    checks: ['table_scope', 'source_values', 'request_alignment', 'calculation'],
  } as const
  assert.equal(
    questionVerificationPresentation(
      answer({
        verification: { ...verification, checks: [...verification.checks] },
      }),
    ).tone,
    'verified',
  )
  assert.equal(
    questionVerificationPresentation(
      answer({
        verification: { level: 'request_checked', checks: [] },
      }),
    ).tone,
    'neutral',
  )
})

test('missing or incomplete request checks cannot certify a result', () => {
  for (const checks of [null, undefined, [], ['table_scope'], ['cited_cells']]) {
    const value = answer({
      verification: { level: 'request_checked', checks },
    } as unknown as Partial<WorkbookQuestionAnswer>)
    assert.equal(questionVerificationPresentation(value).tone, 'neutral')
  }
})

test('truncated scope is not upgraded to verified even when citations match', () => {
  const result = questionVerificationPresentation(
    answer({
      status: 'limited',
      limitations: ['대용량 워크북의 일부 셀은 검색 범위에서 제외되었습니다.'],
      verification: { level: 'request_checked', checks: ['table_scope'] },
    }),
  )
  assert.equal(result.tone, 'limited')
})

test('blocked responses cannot show a verified badge even with stale metadata', () => {
  const result = questionVerificationPresentation(
    answer({
      status: 'insufficient_evidence',
      verification: { level: 'request_checked', checks: ['table_scope'] },
    }),
  )
  assert.equal(result.tone, 'neutral')
  assert.equal(result.label, '답변 검증 불가')
})

test('recalculated formula values cannot appear as original verified values', () => {
  const result = questionVerificationPresentation(
    answer({
      verification: {
        level: 'request_checked',
        checks: ['bounded_recalculation', 'table_scope', 'source_values', 'metric'],
      },
    }),
  )
  assert.equal(result.tone, 'limited')
  assert.equal(result.label, '수식 재계산')
})

test('source ambiguity is presented as an actionable clarification', () => {
  const result = questionVerificationPresentation(
    answer({
      status: 'insufficient_evidence',
      selectedTools: ['clarify_source_scope'],
    }),
  )
  assert.equal(result.label, '대상 확인 필요')
  assert.equal(result.tone, 'neutral')
})

test('header placement is not presented as proof of semantic equivalence', () => {
  const result = questionVerificationPresentation(
    answer({
      status: 'limited',
      selectedTools: ['inspect_header_relation'],
      verification: {
        level: 'source_checked',
        checks: ['cited_cells', 'header_labels', 'header_positions'],
      },
    }),
  )
  assert.equal(result.label, '항목 구조 확인')
  assert.equal(result.tone, 'limited')
  assert.match(result.explanation, /동일 여부를 확인한 것은 아닙니다/)
})
