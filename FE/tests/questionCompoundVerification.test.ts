import assert from 'node:assert/strict'
import test from 'node:test'

import type { WorkbookQuestionAnswer } from '../src/api/analysis/questionTypes.ts'
import { questionVerificationPresentation } from '../src/components/analysis/result/questions/questionVerification.ts'

const answer = (): WorkbookQuestionAnswer => ({
  question: 'Amount 합계; Quantity 평균',
  answer: '문항별 원본 계산 결과',
  status: 'answered',
  confidence: 1,
  selectedTools: ['composite_question', 'tabular_query'],
  evidence: [1, 2].map((part) => ({
    kind: 'cell',
    sheetName: 'Data',
    reference: `B${part + 1}`,
    description: '원본',
    value: 100,
    formula: null,
    label: `문항 ${part} · 값`,
  })),
  limitations: [],
  verification: {
    level: 'request_checked',
    checks: [
      'compound_request_coverage',
      'independent_subquestions',
      'compound_parts_2',
      'request_alignment',
      'table_scope',
      'source_values',
      'calculation',
      'unit',
    ],
  },
})

test('compound badge requires coverage and separate evidence for every part', () => {
  assert.equal(questionVerificationPresentation(answer()).tone, 'verified')
  for (const missing of [
    'compound_request_coverage',
    'independent_subquestions',
    'compound_parts_2',
    'request_alignment',
  ]) {
    const value = answer()
    value.verification!.checks = value.verification!.checks.filter(
      (check) => check !== missing,
    )
    assert.notEqual(questionVerificationPresentation(value).tone, 'verified', missing)
  }
  for (const evidence of [
    [],
    answer().evidence.slice(0, 1),
    answer().evidence.map((item) => ({ ...item, label: '문항 1 · 값' })),
  ]) {
    assert.notEqual(
      questionVerificationPresentation({ ...answer(), evidence }).tone,
      'verified',
    )
  }
})

test('a partial answer never borrows successful tabular checks for the whole answer', () => {
  for (const changes of [
    { status: 'limited' as const },
    { limitations: ['문항 2 확인 불가'] },
    {
      verification: {
        level: 'source_checked' as const,
        checks: answer().verification!.checks,
      },
    },
  ])
    assert.notEqual(
      questionVerificationPresentation({ ...answer(), ...changes }).tone,
      'verified',
    )
})

test('wrong or contradictory part counts cannot be verified', () => {
  for (const count of ['compound_parts_3', 'compound_parts_4', 'compound_parts_9']) {
    const value = answer()
    value.verification!.checks = value
      .verification!.checks.filter((check) => check !== 'compound_parts_2')
      .concat(count)
    assert.notEqual(questionVerificationPresentation(value).tone, 'verified')
  }
  const value = answer()
  value.verification!.checks.push('compound_parts_3')
  assert.notEqual(questionVerificationPresentation(value).tone, 'verified')
})
