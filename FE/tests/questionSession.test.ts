import assert from 'node:assert/strict'
import test from 'node:test'

import {
  createQuestionSession,
  reduceQuestionSession,
} from '../src/hooks/analysis/questionSession.ts'
import { questionAnswer } from './questionContext.fixtures.ts'

test('a new analysis starts with no previous answers, pending state or errors', () => {
  let previous = createQuestionSession('analysis-a')
  previous = reduceQuestionSession(previous, {
    scope: previous.scope,
    type: 'success',
    answer: questionAnswer(),
  })
  previous = reduceQuestionSession(previous, {
    scope: previous.scope,
    type: 'start',
    question: '후속 질문',
  })
  previous = reduceQuestionSession(previous, {
    scope: previous.scope,
    type: 'error',
    message: '오류',
  })
  const next = createQuestionSession('analysis-b')
  assert.equal(previous.answers.length, 1)
  assert.deepEqual(next.answers, [])
  assert.equal(next.pendingQuestion, null)
  assert.equal(next.errorMessage, null)
  assert.equal(next.validationMessage, null)
})

test('late response and error from a previous analysis never alter the new session', () => {
  const previous = createQuestionSession('analysis-a')
  const next = createQuestionSession('analysis-b')
  assert.equal(
    reduceQuestionSession(next, {
      scope: previous.scope,
      type: 'success',
      answer: questionAnswer(),
    }),
    next,
  )
  assert.equal(
    reduceQuestionSession(next, {
      scope: previous.scope,
      type: 'error',
      message: '오류',
    }),
    next,
  )
  assert.equal(
    reduceQuestionSession(next, { scope: previous.scope, type: 'settled' }),
    next,
  )
})

test('returning to the same analysis does not accept its earlier in-flight response', () => {
  const previous = createQuestionSession('analysis-a')
  const returned = createQuestionSession('analysis-a')
  assert.equal(
    reduceQuestionSession(returned, {
      scope: previous.scope,
      type: 'success',
      answer: questionAnswer(),
    }),
    returned,
  )
})

test('current session records answers and settled state without clearing conversation', () => {
  let session = createQuestionSession('analysis-a')
  const scope = session.scope
  session = reduceQuestionSession(session, { scope, type: 'start', question: '매출은?' })
  assert.equal(session.pendingQuestion, '매출은?')
  session = reduceQuestionSession(session, {
    scope,
    type: 'success',
    answer: questionAnswer(),
  })
  session = reduceQuestionSession(session, { scope, type: 'settled' })
  assert.equal(session.answers.length, 1)
  assert.equal(session.pendingQuestion, null)
})
