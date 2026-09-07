import assert from 'node:assert/strict'
import test from 'node:test'

import type {
  InsightReportResult,
  InsightResult,
} from '../src/api/analysis/insightTypes.ts'
import { prepareInsightReportPresentation } from '../src/components/analysis/result/insightReportPresentation.ts'

const REMOVED_CAUSE_REASON =
  '원인을 직접 입증하는 수식·메타데이터 근거가 없어 원인 문장을 제외했습니다.'

const insight = (changes: Partial<InsightResult> = {}): InsightResult => ({
  title: '식단 정보',
  fact: '급식표에 영양량이 표시되어 있습니다.',
  category: 'summary',
  severity: 'info',
  evidence: ['Sheet1!C6:O6'],
  confidence: 0.9,
  validationStatus: 'verified',
  validationReasons: [],
  isIncomplete: false,
  cause: null,
  impact: null,
  recommendation: null,
  ...changes,
})

const report = (insights: InsightResult[]): InsightReportResult => ({
  overview: 'Riot Games의 직원 수가 감소했습니다.',
  insights,
  limitations: ['기업의 시장 비교 자료가 없습니다.'],
  hasIncompleteData: false,
  validation: {
    generatedCount: insights.length,
    verifiedCount: 99,
    limitedCount: 99,
    blockedCount: 0,
    notices: [],
  },
})

test('숨긴 과거 주장과 권고를 요약·분석 한계에서도 노출하지 않는다', () => {
  const source = report([
    insight({
      title: '직원 수 감소',
      fact: 'Riot Games의 직원 수가 6,101명에서 5,417명으로 감소했습니다.',
      recommendation: '인력 감축 계획을 검토하세요.',
      validationStatus: 'limited',
      validationReasons: ['일부 수치 표현을 분석 입력에서 자동으로 대조하지 못했습니다.'],
    }),
    insight(),
  ])
  const { report: visible, hasSuppressedInsights } =
    prepareInsightReportPresentation(source)
  assert.equal(hasSuppressedInsights, true)
  assert.equal(visible.insights.length, 1)
  assert.equal(visible.overview, visible.insights[0].fact)
  assert.doesNotMatch(JSON.stringify(visible), /Riot|인력 감축|기업의 시장/)
  assert.deepEqual(
    [
      visible.validation?.verifiedCount,
      visible.validation?.limitedCount,
      visible.validation?.blockedCount,
    ],
    [1, 0, 1],
  )
  assert.equal(source.insights.length, 2)
  assert.match(source.overview, /Riot/)
})

test('원인만 제거한 LIMITED 사실은 유지하되 파생 원인·검토·권고는 숨긴다', () => {
  const source = report([
    insight({
      validationStatus: 'limited',
      validationReasons: [REMOVED_CAUSE_REASON],
      cause: '저장된 원인',
      impact: '원인에서 파생된 영향',
      recommendation: '원인에서 파생된 권고',
    }),
  ])
  const { report: visible } = prepareInsightReportPresentation(source)
  assert.equal(visible.insights.length, 1)
  assert.equal(visible.insights[0].validationStatus, 'limited')
  assert.equal(visible.insights[0].cause, null)
  assert.equal(visible.insights[0].impact, null)
  assert.equal(visible.insights[0].recommendation, null)
  assert.equal(visible.validation?.verifiedCount, 0)
  assert.equal(visible.validation?.limitedCount, 1)
})

test('알 수 없는 구버전 판정과 해석되지 않은 근거를 검증 완료로 표시하지 않는다', () => {
  for (const candidate of [
    insight({ validationStatus: null }),
    insight({ validationStatus: 'limited' }),
    insight({
      validationReasons: [
        '일부 근거 위치를 자동으로 해석하지 못해 원본 위치 확인이 필요합니다.',
      ],
    }),
    insight({
      validationReasons: [
        '일부 셀·범위가 분석 입력과 정확히 일치하지 않아 원본 확인이 필요합니다.',
      ],
    }),
    insight({ fact: '' }),
    insight({ evidence: [] }),
  ]) {
    const source = { ...report([candidate]), validation: null }
    const { report: visible, hasSuppressedInsights } =
      prepareInsightReportPresentation(source)
    assert.equal(hasSuppressedInsights, true)
    assert.equal(visible.insights.length, 0)
    assert.equal(visible.validation?.verifiedCount, 0)
    assert.match(visible.limitations.join(' '), /다시 분석/)
    assert.doesNotMatch(visible.overview, /Riot/)
  }
})

test('이미 검증된 결과는 유지하고 기존 배제 건수에 새 배제 건수만 더한다', () => {
  const source = report([insight(), insight({ validationStatus: null })])
  source.validation!.blockedCount = 2
  source.validation!.generatedCount = 4
  const { report: visible } = prepareInsightReportPresentation(source)
  assert.equal(visible.insights[0], source.insights[0])
  assert.equal(visible.validation?.blockedCount, 3)
  assert.equal(visible.validation?.generatedCount, 4)
  const repeated = prepareInsightReportPresentation(visible).report
  assert.equal(repeated.validation?.blockedCount, 3)
})
