import assert from 'node:assert/strict'
import test from 'node:test'

import {
  type InsightResult,
  normalizeInsightReport,
} from '../src/api/analysis/insightTypes.ts'
import { groupInsights } from '../src/components/analysis/result/insightGroupPresentation.ts'

const insight = (changes: Partial<InsightResult>): InsightResult => ({
  title: '원본에서 확인한 내용',
  topic: null,
  fact: '원본 셀 값으로 확인했습니다.',
  cause: null,
  impact: null,
  category: 'summary',
  severity: 'info',
  evidence: ['Sheet1!A1'],
  recommendation: null,
  confidence: 1,
  isIncomplete: false,
  validationStatus: 'verified',
  validationReasons: [],
  ...changes,
})

test('인사이트를 핵심 지표, 기간별 추이, 시점 간 증감, 이상징후, 추가 내용 순서로 그룹화한다', () => {
  const groups = groupInsights([
    insight({ category: 'summary' }),
    insight({ category: 'risk' }),
    insight({ category: 'trend' }),
    insight({ category: 'change' }),
    insight({ category: 'metric' }),
  ])

  assert.deepEqual(
    groups.map(({ key }) => key),
    ['metric', 'trend', 'change', 'anomaly', 'additional'],
  )
  assert.equal(groups[0].description, '결론을 뒷받침하는 중요한 수치와 비교 결과입니다.')
  assert.equal(groups[1].title, '주제 확인 불가')
  assert.equal(groups[2].title, '주제 확인 불가')
})

test('주의·긴급 인사이트는 category와 무관하게 이상징후로 표시한다', () => {
  const groups = groupInsights([
    insight({ category: 'formula', severity: 'warning' }),
    insight({ category: 'structure', severity: 'critical' }),
    insight({ category: 'trend', severity: 'warning' }),
  ])

  assert.equal(groups.length, 1)
  assert.equal(groups[0].key, 'anomaly')
  assert.equal(groups[0].insights.length, 3)
})

test('비어 있는 그룹은 화면 모델에서 제외한다', () => {
  const groups = groupInsights([insight({ category: 'trend' })])

  assert.deepEqual(
    groups.map(({ key }) => key),
    ['trend'],
  )
})

test('새 category는 보존하고 알 수 없는 값은 summary로 정규화한다', () => {
  const report = normalizeInsightReport({
    overview: '검증된 요약',
    insights: [
      insight({ category: 'metric' }),
      insight({ category: 'trend' }),
      insight({ category: 'change' }),
      { ...insight({}), category: 'unknown' },
    ],
    limitations: [],
  })

  assert.deepEqual(
    report?.insights.map(({ category }) => category),
    ['metric', 'trend', 'change', 'summary'],
  )
})

test('이전 분석 결과의 항목별 비교 카드를 증감 비교로 보여준다', () => {
  const report = normalizeInsightReport({
    overview: '요약',
    insights: [insight({ title: '주요 항목별 변화', category: 'trend' })],
  })

  assert.equal(report?.insights[0].category, 'change')
  assert.equal(groupInsights(report?.insights ?? [])[0].key, 'change')
})

test('실제 인사이트 주제를 섹션 제목에 반영하고 분류명만 제목으로 쓰지 않는다', () => {
  const groups = groupInsights([
    insight({ category: 'trend', topic: '전체 직원 수', title: '전체 직원 수 변화' }),
    insight({
      category: 'change',
      topic: '부서별 직원 수',
      title: '부서별 직원 수 변화',
    }),
  ])

  assert.deepEqual(
    groups.map(({ title }) => title),
    ['전체 직원 수 추이', '부서별 직원 수 증감'],
  )
})

test('같은 분류에 서로 다른 주제가 있으면 한 주제로 단정하지 않는다', () => {
  const groups = groupInsights([
    insight({ category: 'metric', topic: '매출액' }),
    insight({ category: 'metric', topic: '순이익' }),
  ])

  assert.equal(groups[0].title, '매출액 · 순이익')
})

test('서로 다른 종류의 엑셀 주제를 정규화부터 화면 제목까지 유지한다', () => {
  for (const [topic, category, expected] of [
    ['거래가격', 'metric', '거래가격'],
    ['사건 유형', 'summary', '사건 유형'],
    ['월별 전력 사용량', 'trend', '월별 전력 사용량 추이'],
  ] as const) {
    const report = normalizeInsightReport({
      overview: '원본 자료 요약',
      insights: [{ ...insight({ category }), topic }],
    })

    assert.equal(report?.insights[0].topic, topic)
    assert.equal(groupInsights(report?.insights ?? [])[0].title, expected)
  }
})

test('주제가 많아도 제목을 무한히 이어 붙이지 않는다', () => {
  const groups = groupInsights([
    insight({ category: 'metric', topic: '매출액' }),
    insight({ category: 'metric', topic: '순이익' }),
    insight({ category: 'metric', topic: '영업이익' }),
    insight({ category: 'metric', topic: '총자산' }),
  ])

  assert.equal(groups[0].title, '매출액 · 순이익 외 2개 주제')
  assert.equal(groups[0].insights.length, 4)
})

test('원본에서 주제를 확인하지 못하면 빈 상투어를 주제로 내세우지 않는다', () => {
  const groups = groupInsights([insight({ title: '원본에서 확인한 내용', topic: null })])
  assert.equal(groups[0].title, '주제 확인 불가')
})
