import assert from 'node:assert/strict'
import test from 'node:test'

import {
  type InsightResult,
  normalizeInsightReport,
} from '../src/api/analysis/insightTypes.ts'
import { groupInsights } from '../src/components/analysis/result/insightGroupPresentation.ts'

const insight = (changes: Partial<InsightResult>): InsightResult => ({
  title: '원본에서 확인한 내용',
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

test('인사이트를 핵심 지표, 추세, 이상징후, 추가 내용 순서로 그룹화한다', () => {
  const groups = groupInsights([
    insight({ category: 'summary' }),
    insight({ category: 'risk' }),
    insight({ category: 'trend' }),
    insight({ category: 'metric' }),
  ])

  assert.deepEqual(
    groups.map(({ key }) => key),
    ['metric', 'trend', 'anomaly', 'additional'],
  )
  assert.equal(groups[0].description, '결론을 뒷받침하는 중요한 수치와 비교 결과입니다.')
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
      { ...insight({}), category: 'unknown' },
    ],
    limitations: [],
  })

  assert.deepEqual(
    report?.insights.map(({ category }) => category),
    ['metric', 'trend', 'summary'],
  )
})
