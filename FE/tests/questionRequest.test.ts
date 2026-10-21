import assert from 'node:assert/strict'
import test from 'node:test'

import type { WorkbookQuestionAnswer } from '../src/api/analysis/questionTypes.ts'
import { executeQuestionRequest } from '../src/hooks/analysis/questionRequest.ts'
import {
  createQuestionSession,
  reduceQuestionSession,
} from '../src/hooks/analysis/questionSession.ts'
import { questionAnswer } from './questionContext.fixtures.ts'

const deferred = () => {
  let resolve!: (answer: WorkbookQuestionAnswer) => void
  let reject!: (reason: unknown) => void
  const promise = new Promise<WorkbookQuestionAnswer>((yes, no) => {
    resolve = yes
    reject = no
  })
  return { promise, resolve, reject }
}

const harness = () => {
  let session = createQuestionSession('analysis-a', 'owner-a')
  let active: object | undefined = session.scope
  let released = false
  const request = deferred()
  const options = {
    scope: session.scope,
    request: () => request.promise,
    isActive: () => active === options.scope,
    update: (action: Parameters<typeof reduceQuestionSession>[1]) => {
      session = reduceQuestionSession(session, action)
    },
    errorMessage: () => '연결 실패',
    release: () => {
      released = true
    },
  }
  options.update({ scope: session.scope, type: 'start', question: '매출은?' })
  return {
    request,
    options,
    get session() {
      return session
    },
    get released() {
      return released
    },
    switchTo(analysisId: string, ownerId: string) {
      session = createQuestionSession(analysisId, ownerId)
      active = session.scope
    },
    unmount() {
      active = undefined
    },
  }
}

for (const [name, analysisId, ownerId] of [
  ['a different workbook', 'analysis-b', 'owner-a'],
  ['a different owner', 'analysis-a', 'owner-b'],
  ['a re-entered workbook', 'analysis-a', 'owner-a'],
] as const) {
  test(`late success cannot report acceptance or clear a draft in ${name}`, async () => {
    const state = harness()
    const pending = executeQuestionRequest(state.options)
    state.switchTo(analysisId, ownerId)
    const next = state.session
    state.request.resolve(questionAnswer())
    assert.equal(await pending, false)
    assert.equal(state.session, next)
    assert.equal(state.released, true)
  })
}

test('unmounted request completion is not reported as a successful active submission', async () => {
  const state = harness()
  const pending = executeQuestionRequest(state.options)
  state.unmount()
  state.request.resolve(questionAnswer())
  assert.equal(await pending, false)
  assert.deepEqual(state.session.answers, [])
  assert.equal(state.released, true)
})

test('current success appends exactly one answer and settles its pending state', async () => {
  const state = harness()
  const pending = executeQuestionRequest(state.options)
  const answer = questionAnswer()
  state.request.resolve(answer)
  assert.equal(await pending, true)
  assert.deepEqual(state.session.answers, [answer])
  assert.equal(state.session.pendingQuestion, null)
  assert.equal(state.released, true)
})

test('current request failure clears pending and preserves conversation for retry', async () => {
  const state = harness()
  const answer = questionAnswer()
  state.options.update({ scope: state.session.scope, type: 'success', answer })
  const pending = executeQuestionRequest(state.options)
  state.request.reject(new Error('offline'))
  assert.equal(await pending, false)
  assert.equal(state.session.pendingQuestion, null)
  assert.equal(state.session.errorMessage, '연결 실패')
  assert.deepEqual(state.session.answers, [answer])
  assert.equal(state.released, true)
})

test('old request errors do not change new session errors or pending state', async () => {
  const state = harness()
  const pending = executeQuestionRequest(state.options)
  state.switchTo('analysis-b', 'owner-a')
  state.options.update({ scope: state.session.scope, type: 'start', question: '새 질문' })
  const next = state.session
  state.request.reject(new Error('old timeout'))
  assert.equal(await pending, false)
  assert.equal(state.session, next)
  assert.equal(state.session.pendingQuestion, '새 질문')
})
