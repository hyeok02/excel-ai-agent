import assert from 'node:assert/strict'
import test from 'node:test'

import {
  buildClarificationRequest,
  getClarificationOptions,
} from '../src/components/analysis/result/questions/questionClarification.ts'
import { buildQuestionContext } from '../src/components/analysis/result/questions/questionContext.ts'
import { questionAnswer } from './questionContext.fixtures.ts'

const option = {
  id: 'a'.repeat(64),
  label: '매출 (USD)',
  scope: '실적!B1:B5',
  details: '통화 USD',
  question: '실적 시트의 매출 (USD) 합계는?',
}
const clarification = () =>
  questionAnswer({
    status: 'insufficient_evidence',
    clarificationOptions: [option],
  })

test('only structured clarification options become actions, never prose or verified answers', () => {
  assert.deepEqual(getClarificationOptions(clarification()), [option])
  assert.deepEqual(
    getClarificationOptions(questionAnswer({ answer: JSON.stringify(option) })),
    [],
  )
  assert.deepEqual(
    getClarificationOptions(questionAnswer({ clarificationOptions: [option] })),
    [],
  )
  assert.deepEqual(
    getClarificationOptions(questionAnswer({ status: 'insufficient_evidence' })),
    [],
  )
})

test('choosing an option sends the canonical question with bounded source selection', () => {
  const answer = clarification()
  const request = buildClarificationRequest([answer], answer, option.id, null)
  assert.equal(request?.question, option.question)
  assert.deepEqual(request?.context.selection, {
    source_question: answer.question,
    option_id: option.id,
  })
  assert.equal(request?.context.turns[0].needs_clarification, true)
  assert.doesNotMatch(JSON.stringify(request), /999999|검증되지 않은 이전 답변/)
})

test('a clarification of a follow-up binds to the resolved source question', () => {
  const answer = {
    ...clarification(),
    question: '그 합계는?',
    resolvedQuestion: '실적의 매출 합계는?',
  }
  const request = buildClarificationRequest([answer], answer, option.id, null)
  assert.equal(request?.context.selection.source_question, answer.resolvedQuestion)
})

test('foreign or replaced answer instances and unknown choices cannot produce a request', () => {
  const answer = clarification()
  assert.equal(buildClarificationRequest([], answer, option.id, null), null)
  assert.equal(buildClarificationRequest([answer], { ...answer }, option.id, null), null)
  assert.equal(buildClarificationRequest([answer], answer, 'b'.repeat(64), null), null)
  const oversized = { ...answer, resolvedQuestion: 'x'.repeat(1001) }
  assert.equal(buildClarificationRequest([oversized], oversized, option.id, null), null)
})

test('invalid and oversized structured options are discarded, never truncated into a new action', () => {
  const invalid = [
    { ...option, id: 'A'.repeat(64) },
    { ...option, id: 'a'.repeat(63) },
    { ...option, label: '' },
    { ...option, label: 'x'.repeat(201) },
    { ...option, scope: 'x'.repeat(201) },
    { ...option, details: 'x'.repeat(1001) },
    { ...option, question: 'x' },
    { ...option, question: 'x'.repeat(1001) },
  ]
  for (const item of invalid) {
    assert.deepEqual(
      getClarificationOptions({ ...clarification(), clarificationOptions: [item] }),
      [],
    )
  }
  assert.deepEqual(
    getClarificationOptions({
      ...clarification(),
      clarificationOptions: Array.from({ length: 7 }, () => option),
    }),
    [],
  )
  assert.deepEqual(
    getClarificationOptions({
      ...clarification(),
      clarificationOptions: [option, option],
    }),
    [option],
  )
})

test('the selected result carries resolved evidence forward, but selection is not sticky', () => {
  const answer = clarification()
  const selected = questionAnswer({
    question: option.question,
    resolvedQuestion: option.question,
  })
  const context = buildQuestionContext([answer, selected], null)
  assert.equal(context.turns.at(-1)?.question, option.question)
  assert.deepEqual(context.turns.at(-1)?.evidence, ["'매출 현황'!B2"])
  assert.equal(context.selection, undefined)
})
