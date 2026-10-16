import assert from 'node:assert/strict'
import test from 'node:test'

import { questionVerificationPresentation } from '../src/components/analysis/result/questions/questionVerification.ts'
import {
  createQuestionSession,
  reduceQuestionSession,
} from '../src/hooks/analysis/questionSession.ts'
import { questionAnswer } from './questionContext.fixtures.ts'
import {
  historyPage,
  numberedAnswer,
  restoredSession,
} from './questionHistory.fixtures.ts'

test('restoration preserves answer content, resolved scope, evidence and verification without promotion', () => {
  const answers = [
    questionAnswer({
      resolvedQuestion: '회사 A의 2025년 연간 매출은?',
      status: 'limited',
      selectedTools: ['tabular_query'],
      verification: {
        level: 'request_checked',
        checks: ['table_scope', 'source_values', 'request_alignment', 'context_resolved'],
      },
      limitations: ['앞선 질문의 회사와 기간을 연결해 해석했습니다.'],
      evidence: [
        {
          kind: 'cell',
          sheetName: "회사 A's 매출",
          reference: 'C12',
          description: '연간 매출 원본',
          value: 1234.5,
          formula: '=SUM(C2:C11)',
          label: '1,234.5',
          numberFormat: '#,##0.0',
        },
      ],
    }),
    questionAnswer({
      status: 'insufficient_evidence',
      verification: { level: 'unverified', checks: [] },
      selectedTools: ['clarify_source_scope'],
      limitations: ['원하는 시트를 지정해주세요.'],
    }),
  ]
  const before = structuredClone(answers)
  const session = restoredSession(answers, null)

  assert.equal(session.historyStatus, 'ready')
  assert.deepEqual(session.answers, before)
  assert.deepEqual(answers, before)
  for (const [index, answer] of session.answers.entries()) {
    assert.deepEqual(
      questionVerificationPresentation(answer),
      questionVerificationPresentation(before[index]),
    )
    assert.notEqual(questionVerificationPresentation(answer).tone, 'verified')
  }
})

test('empty saved history finishes restoration with no answers or earlier cursor', () => {
  const session = restoredSession([], null)
  assert.equal(session.historyStatus, 'ready')
  assert.deepEqual(session.answers, [])
  assert.equal(session.nextCursor, null)
  assert.equal(session.historyErrorMessage, null)
  assert.equal(session.pendingQuestion, null)
})

test('initial restore failure remains distinct from question errors and can be retried', () => {
  let session = createQuestionSession('analysis-a', 'owner-a')
  const { scope } = session
  session = reduceQuestionSession(session, {
    scope,
    type: 'restoreError',
    message: '대화 이력을 불러오지 못했습니다.',
  })
  assert.equal(session.historyStatus, 'error')
  assert.equal(session.historyErrorMessage, '대화 이력을 불러오지 못했습니다.')
  assert.equal(session.errorMessage, null)
  assert.deepEqual(session.answers, [])

  session = reduceQuestionSession(session, { scope, type: 'restoreStart' })
  assert.equal(session.historyStatus, 'loading')
  assert.equal(session.historyErrorMessage, null)
  session = reduceQuestionSession(session, {
    scope,
    type: 'restoreSuccess',
    page: historyPage([numberedAnswer(1)]),
  })
  assert.equal(session.historyStatus, 'ready')
  assert.deepEqual(session.answers, [numberedAnswer(1)])
})
