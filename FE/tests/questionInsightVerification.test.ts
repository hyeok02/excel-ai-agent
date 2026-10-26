import assert from 'node:assert/strict'
import test from 'node:test'

import type { WorkbookQuestionAnswer } from '../src/api/analysis/questionTypes.ts'
import { questionVerificationPresentation } from '../src/components/analysis/result/questions/questionVerification.ts'

const insightAnswer = (
  status: WorkbookQuestionAnswer['status'],
): WorkbookQuestionAnswer => ({
  question: '항목별 인원 변화 알려줘',
  answer: '연구개발은 100명에서 120명으로 증가했습니다.',
  status,
  confidence: 1,
  selectedTools: ['search_workbook_data'],
  evidence: [
    {
      kind: 'cell',
      sheetName: 'Data',
      reference: 'B2',
      description: '연구개발',
      value: 120,
      formula: null,
      label: '원본 값: 120',
    },
  ],
  limitations:
    status === 'limited' ? ['일부 관련 셀은 검색 범위에서 제외되었습니다.'] : [],
  verification: {
    level: 'source_checked',
    checks: ['cited_cells', 'verified_insight_fact'],
  },
})

test('reusing a source-checked insight shows source comparison without a green badge', () => {
  const result = questionVerificationPresentation(insightAnswer('answered'))
  assert.equal(result.label, '인용 원본 대조')
  assert.equal(result.tone, 'neutral')
  assert.match(result.explanation, /질문 범위 전체를 검증한 것은 아닙니다/)
})

test('partial insight reuse keeps its limitation badge', () => {
  const result = questionVerificationPresentation(insightAnswer('limited'))
  assert.equal(result.label, '일부 범위만 대조')
  assert.equal(result.tone, 'limited')
})

test('insight source metadata cannot make a blocked answer verified', () => {
  const result = questionVerificationPresentation(insightAnswer('insufficient_evidence'))
  assert.equal(result.label, '답변 검증 불가')
  assert.equal(result.tone, 'neutral')
})
