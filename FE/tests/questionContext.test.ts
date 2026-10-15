import assert from 'node:assert/strict'
import test from 'node:test'

import {
  buildQuestionContext,
  resolvedQuestionLabel,
} from '../src/components/analysis/result/questions/questionContext.ts'
import {
  contextInsight,
  contextReport,
  questionAnswer,
} from './questionContext.fixtures.ts'

test('context sends question and source hints, never previous answer or insight facts', () => {
  const context = buildQuestionContext(
    [questionAnswer()],
    contextReport([contextInsight()]),
  )
  assert.deepEqual(context, {
    turns: [{ question: '매출 합계는?', evidence: ["'매출 현황'!B2"] }],
    insights: [{ title: '매출 변화', topic: '매출', evidence: ["'매출 현황'!B2:B4"] }],
  })
  assert.doesNotMatch(JSON.stringify(context), /999999|888888|전체 요약|원인|설명/)
})

test('multi-turn context retains the resolved question instead of an unresolved pronoun', () => {
  const answer = questionAnswer({
    question: '그중 최대는?',
    resolvedQuestion: '매출 중 최대는?',
  })
  assert.equal(buildQuestionContext([answer], null).turns[0].question, '매출 중 최대는?')
  assert.equal(resolvedQuestionLabel(answer), '매출 중 최대는?')
  assert.equal(resolvedQuestionLabel(questionAnswer()), null)
  assert.equal(
    resolvedQuestionLabel(questionAnswer({ resolvedQuestion: '매출 합계는? ' })),
    null,
  )
})

test('an unanswered turn keeps its clarification state even with candidate evidence', () => {
  const context = buildQuestionContext(
    [questionAnswer({ status: 'insufficient_evidence' })],
    null,
  )
  assert.equal(context.turns[0].needs_clarification, true)
  assert.equal(context.turns[0].evidence.length, 1)
})

test('only six recent questions and six visible verified insights are sent', () => {
  const answers = Array.from({ length: 9 }, (_, i) =>
    questionAnswer({ question: `질문 ${i}` }),
  )
  const insights = Array.from({ length: 9 }, (_, i) =>
    contextInsight({ title: `주제 ${i}` }),
  )
  const context = buildQuestionContext(answers, contextReport(insights))
  assert.deepEqual(
    context.turns.map((turn) => turn.question),
    ['질문 3', '질문 4', '질문 5', '질문 6', '질문 7', '질문 8'],
  )
  assert.equal(context.insights.length, 6)
})

test('hidden, unverifiable and legacy limited insights cannot seed follow-up context', () => {
  const hidden = [
    contextInsight({ validationStatus: null }),
    contextInsight({ validationStatus: 'limited', validationReasons: ['수치 불일치'] }),
    contextInsight({ validationStatus: 'limited', validationReasons: [] }),
    contextInsight({ fact: '' }),
    contextInsight({ evidence: [] }),
  ]
  assert.deepEqual(buildQuestionContext([], contextReport(hidden)).insights, [])
  const limited = contextInsight({
    validationStatus: 'limited',
    validationReasons: [
      '원인을 직접 입증하는 수식·메타데이터 근거가 없어 원인 문장을 제외했습니다.',
    ],
  })
  assert.equal(buildQuestionContext([], contextReport([limited])).insights.length, 1)
})

test('reference hints preserve spaces, quotes and exclamation marks with Excel quoting', () => {
  const base = questionAnswer()
  const answer = questionAnswer({
    evidence: [
      { ...base.evidence[0], sheetName: "O'Brien! 매출", reference: '$b$2:$c$4' },
    ],
  })
  const report = contextReport([
    contextInsight({ evidence: ["'O''Brien! 매출'!$b$2:$c$4"] }),
  ])
  const context = buildQuestionContext([answer], report)
  assert.deepEqual(context.turns[0].evidence, ["'O''Brien! 매출'!B2:C4"])
  assert.deepEqual(context.insights[0].evidence, context.turns[0].evidence)
})

test('reference hints are deduplicated, bounded and malformed refs are excluded', () => {
  const refs = [
    'Sheet1!A1',
    'Sheet1!A1',
    'bad',
    'Sheet1!instructions',
    ...Array.from({ length: 30 }, (_, i) => `Sheet1!B${i + 1}`),
  ]
  const context = buildQuestionContext(
    [],
    contextReport([contextInsight({ evidence: refs })]),
  )
  assert.equal(context.insights[0].evidence.length, 12)
  assert.equal(context.insights[0].evidence[0], "'Sheet1'!A1")
  assert.ok(context.insights[0].evidence.every((reference) => reference.length <= 200))
})

test('overlong hints are omitted, never truncated into a different target', () => {
  const long = 'x'.repeat(1001)
  const context = buildQuestionContext(
    [questionAnswer({ question: long }), questionAnswer({ resolvedQuestion: long })],
    contextReport([
      contextInsight({ title: 'x'.repeat(201) }),
      contextInsight({ topic: 'x'.repeat(201) }),
      contextInsight({ evidence: [`${'x'.repeat(201)}!A1`] }),
    ]),
  )
  assert.equal(context.turns.length, 1)
  assert.equal(context.turns[0].question, '매출 합계는?')
  assert.equal(context.insights.length, 1)
  assert.equal(context.insights[0].topic, null)
})
