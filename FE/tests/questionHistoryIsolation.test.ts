import assert from 'node:assert/strict'
import test from 'node:test'

import { buildQuestionContext } from '../src/components/analysis/result/questions/questionContext.ts'
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

for (const [name, analysisId, ownerId] of [
  ['analysis changes', 'analysis-b', 'owner-a'],
  ['account changes', 'analysis-a', 'owner-b'],
  ['A to B to A returns', 'analysis-a', 'owner-a'],
] as const) {
  test(`${name} reject late restoration, pagination and error state from the old session`, () => {
    const oldSession = restoredSession()
    const next = createQuestionSession(analysisId, ownerId)
    assert.notEqual(next.scope, oldSession.scope)
    assert.equal(next.ownerId, ownerId)
    assert.deepEqual(next.answers, [])
    const lateActions = [
      { type: 'restoreSuccess', page: historyPage([numberedAnswer(9)]) },
      { type: 'restoreError', message: 'old restore failed' },
      { type: 'earlierSuccess', before: '3', page: historyPage([numberedAnswer(1)]) },
      { type: 'earlierError', message: 'old earlier page failed' },
      { type: 'earlierSettled' },
    ] as const
    for (const action of lateActions) {
      assert.equal(
        reduceQuestionSession(next, { scope: oldSession.scope, ...action }),
        next,
      )
    }
  })
}

test('restored and prepended history sends only the last six scoped questions and references', () => {
  const recent = Array.from({ length: 6 }, (_, index) => numberedAnswer(index + 3))
  recent[5] = questionAnswer({
    ...numberedAnswer(8),
    status: 'insufficient_evidence',
    selectedTools: ['clarify_source_scope'],
  })
  let session = restoredSession(recent)
  const originalContext = buildQuestionContext(session.answers, null)
  session = reduceQuestionSession(session, {
    scope: session.scope,
    type: 'earlierSuccess',
    before: '3',
    page: historyPage([numberedAnswer(1), numberedAnswer(2)]),
  })
  const context = buildQuestionContext(session.answers, null)

  assert.deepEqual(context, originalContext)
  assert.equal(context.turns.length, 6)
  assert.deepEqual(
    context.turns.map((turn) => turn.question),
    recent.map((answer) => answer.resolvedQuestion),
  )
  assert.equal(context.turns.at(-1)?.needs_clarification, true)
  assert.deepEqual(context.turns[0].evidence, ["'매출 현황'!B2"])
  assert.deepEqual(context.insights, [])
  const serialized = JSON.stringify(context)
  assert.equal(serialized.includes('검증되지 않은 이전 답변'), false)
  assert.equal(serialized.includes('999999'), false)
  assert.equal(serialized.includes('설명은 전달하지 않음'), false)
})
