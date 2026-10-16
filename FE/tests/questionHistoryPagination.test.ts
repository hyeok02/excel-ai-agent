import assert from 'node:assert/strict'
import test from 'node:test'

import { reduceQuestionSession } from '../src/hooks/analysis/questionSession.ts'
import {
  historyPage,
  numberedAnswer,
  restoredSession,
} from './questionHistory.fixtures.ts'

test('older pages prepend chronologically and the same completed cursor is ignored', () => {
  let session = restoredSession()
  const { scope } = session
  const olderPage = historyPage([numberedAnswer(1), numberedAnswer(2)], null)
  session = reduceQuestionSession(session, { scope, type: 'earlierStart' })
  assert.equal(session.loadingEarlier, true)
  session = reduceQuestionSession(session, {
    scope,
    type: 'earlierSuccess',
    before: '3',
    page: olderPage,
  })
  assert.deepEqual(
    session.answers.map((answer) => answer.question),
    ['질문 1', '질문 2', '질문 3', '질문 4'],
  )
  assert.equal(session.nextCursor, null)
  assert.equal(
    reduceQuestionSession(session, {
      scope,
      type: 'earlierSuccess',
      before: '3',
      page: olderPage,
    }),
    session,
  )
  session = reduceQuestionSession(session, { scope, type: 'earlierSettled' })
  assert.equal(session.loadingEarlier, false)
})

test('cursor strings above the JavaScript safe integer limit are preserved exactly', () => {
  const cursor = '9007199254740993'
  let session = restoredSession([numberedAnswer(3)], cursor)
  assert.equal(session.nextCursor, cursor)
  assert.equal(
    reduceQuestionSession(session, {
      scope: session.scope,
      type: 'earlierSuccess',
      before: '9007199254740992',
      page: historyPage([numberedAnswer(1)]),
    }),
    session,
  )
  session = reduceQuestionSession(session, {
    scope: session.scope,
    type: 'earlierSuccess',
    before: cursor,
    page: historyPage([numberedAnswer(2)]),
  })
  assert.deepEqual(
    session.answers.map((answer) => answer.question),
    ['질문 2', '질문 3'],
  )
})

test('new answer returned while an older page loads remains the latest answer', () => {
  let session = restoredSession()
  const { scope } = session
  session = reduceQuestionSession(session, { scope, type: 'earlierStart' })
  session = reduceQuestionSession(session, { scope, type: 'start', question: '질문 5' })
  session = reduceQuestionSession(session, {
    scope,
    type: 'success',
    answer: numberedAnswer(5),
  })
  session = reduceQuestionSession(session, { scope, type: 'settled' })
  session = reduceQuestionSession(session, {
    scope,
    type: 'earlierSuccess',
    before: '3',
    page: historyPage([numberedAnswer(1), numberedAnswer(2)]),
  })
  session = reduceQuestionSession(session, { scope, type: 'earlierSettled' })

  assert.deepEqual(
    session.answers.map((answer) => answer.question),
    ['질문 1', '질문 2', '질문 3', '질문 4', '질문 5'],
  )
  assert.equal(session.answers.at(-1)?.question, '질문 5')
  assert.equal(session.pendingQuestion, null)
  assert.equal(session.loadingEarlier, false)
})

test('older-page failure preserves current answers and cursor for retry', () => {
  let session = restoredSession()
  const { scope } = session
  const currentAnswers = session.answers
  session = reduceQuestionSession(session, { scope, type: 'earlierStart' })
  session = reduceQuestionSession(session, {
    scope,
    type: 'earlierError',
    message: '이전 대화 조회 실패',
  })
  session = reduceQuestionSession(session, { scope, type: 'earlierSettled' })
  assert.equal(session.historyStatus, 'ready')
  assert.equal(session.answers, currentAnswers)
  assert.equal(session.nextCursor, '3')
  assert.equal(session.earlierHistoryErrorMessage, '이전 대화 조회 실패')
  assert.equal(session.historyErrorMessage, null)

  session = reduceQuestionSession(session, { scope, type: 'earlierStart' })
  assert.equal(session.earlierHistoryErrorMessage, null)
  assert.equal(session.loadingEarlier, true)
  session = reduceQuestionSession(session, {
    scope,
    type: 'earlierSuccess',
    before: '3',
    page: historyPage([numberedAnswer(2)]),
  })
  assert.deepEqual(
    session.answers.map((answer) => answer.question),
    ['질문 2', '질문 3', '질문 4'],
  )
})
