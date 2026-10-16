import assert from 'node:assert/strict'
import test from 'node:test'

import { getClarificationOptions } from '../src/components/analysis/result/questions/questionClarification.ts'
import {
  canSubmitQuestion,
  createQuestionSession,
  reduceQuestionSession,
} from '../src/hooks/analysis/questionSession.ts'
import { questionAnswer } from './questionContext.fixtures.ts'
import { historyPage, restoredSession } from './questionHistory.fixtures.ts'

test('submission gates block expired, restoring, unauthenticated, duplicate and stale-scope choices', () => {
  const state = restoredSession()
  assert.equal(canSubmitQuestion(state, state.scope, null, true), true)
  assert.equal(canSubmitQuestion(state, state.scope, null, false), false)
  assert.equal(canSubmitQuestion(state, state.scope, state.scope, true), false)
  assert.equal(canSubmitQuestion(state, {}, null, true), false)
  assert.equal(canSubmitQuestion(state, undefined, null, true), false)
  assert.equal(
    canSubmitQuestion({ ...state, ownerId: null }, state.scope, null, true),
    false,
  )
  assert.equal(
    canSubmitQuestion({ ...state, historyStatus: 'loading' }, state.scope, null, true),
    false,
  )
  assert.equal(
    canSubmitQuestion({ ...state, historyStatus: 'error' }, state.scope, null, true),
    false,
  )
  assert.equal(
    canSubmitQuestion({ ...state, pendingQuestion: '질문' }, state.scope, null, true),
    false,
  )
})

test('restored choices survive roundtrip and selected answers append without replacing clarification', () => {
  const answer = questionAnswer({
    status: 'insufficient_evidence',
    clarificationOptions: [
      {
        id: 'c'.repeat(64),
        label: '매출 (EUR)',
        scope: '원본!C1:C5',
        details: '통화 EUR',
        question: '원본 시트 매출 (EUR) 합계는?',
      },
    ],
  })
  let state = restoredSession(JSON.parse(JSON.stringify([answer])))
  assert.deepEqual(getClarificationOptions(state.answers[0]), answer.clarificationOptions)
  const chosen = questionAnswer({ question: answer.clarificationOptions![0].question })
  state = reduceQuestionSession(state, {
    scope: state.scope,
    type: 'start',
    question: chosen.question,
  })
  state = reduceQuestionSession(state, {
    scope: state.scope,
    type: 'success',
    answer: chosen,
  })
  state = reduceQuestionSession(state, { scope: state.scope, type: 'settled' })
  assert.deepEqual(state.answers, [answer, chosen])
})

for (const [analysis, owner] of [
  ['analysis-b', 'owner-a'],
  ['analysis-a', 'owner-b'],
  ['analysis-a', 'owner-a'],
]) {
  test(`late choice completion cannot contaminate new scope ${analysis}/${owner}`, () => {
    const old = restoredSession()
    const next = createQuestionSession(analysis, owner)
    const restored = reduceQuestionSession(next, {
      scope: next.scope,
      type: 'restoreSuccess',
      page: historyPage([]),
    })
    assert.equal(canSubmitQuestion(old, restored.scope, null, true), false)
    assert.equal(
      reduceQuestionSession(restored, {
        scope: old.scope,
        type: 'success',
        answer: questionAnswer(),
      }),
      restored,
    )
    assert.equal(
      reduceQuestionSession(restored, { scope: old.scope, type: 'settled' }),
      restored,
    )
    assert.equal(canSubmitQuestion(restored, restored.scope, old.scope, true), true)
  })
}
