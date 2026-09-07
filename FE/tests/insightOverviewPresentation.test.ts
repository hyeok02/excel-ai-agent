import assert from 'node:assert/strict'
import test from 'node:test'

import {
  type InsightResult,
  normalizeInsightReport,
} from '../src/api/analysis/insightTypes.ts'
import {
  insightValidationLabel,
  prepareInsightReportPresentation,
} from '../src/components/analysis/result/insightReportPresentation.ts'

const fact = (changes: Partial<InsightResult> = {}) => ({
  title: '급식표 내용',
  fact: '급식표에 식단과 영양량이 기록되어 있습니다.',
  evidence: ['Sheet1!H6:J6'],
  validationStatus: 'verified',
  validationReasons: [],
  confidence: 0.99,
  ...changes,
})

const source = (marker: unknown, insights = [fact()]) =>
  normalizeInsightReport({
    overview: '학교 급식표의 날짜별 식단과 영양량을 확인할 수 있습니다.',
    insights,
    limitations: [],
    validation: {
      overviewValidated: marker,
      generatedCount: insights.length,
      verifiedCount: insights.length,
      limitedCount: 0,
      blockedCount: 0,
      notices: [],
    },
  })!

test('서버가 검증한 설명형 요약은 첫 두 사실로 덮어쓰지 않는다', () => {
  const input = source(true)
  const visible = prepareInsightReportPresentation(input).report
  assert.equal(visible.overview, input.overview)
  assert.notEqual(visible.overview, input.insights[0].fact)
  assert.equal(visible.validation?.overviewValidated, true)
  assert.equal(prepareInsightReportPresentation(visible).report.overview, input.overview)
})

test('과거 기록과 문자열·숫자 마커는 서버 요약 검증으로 인정하지 않는다', () => {
  for (const marker of [undefined, null, false, 'true', 1]) {
    const input = source(marker)
    input.overview = 'Riot Games의 직원 수가 감소했습니다.'
    const visible = prepareInsightReportPresentation(input).report
    assert.equal(visible.overview, input.insights[0].fact)
    assert.equal(visible.validation?.overviewValidated, false)
  }
})

test('마커가 있어도 알 수 없는 사유로 카드가 제외되면 해당 요약을 숨긴다', () => {
  const input = source(true, [
    fact(),
    fact({
      fact: 'Riot Games의 직원 수가 감소했습니다.',
      validationReasons: ['알 수 없는 검증 사유'],
    }),
  ])
  input.overview = 'Riot Games의 직원 수가 감소했습니다.'
  const { report, hasSuppressedInsights } = prepareInsightReportPresentation(input)
  assert.equal(hasSuppressedInsights, true)
  assert.equal(report.overview, input.insights[0].fact)
  assert.equal(report.validation?.overviewValidated, false)
  assert.doesNotMatch(JSON.stringify(report), /Riot/)
})

test('빈 요약과 표시할 사실이 없는 요약은 마커가 있어도 보존하지 않는다', () => {
  const input = source(true)
  input.overview = '  '
  assert.equal(
    prepareInsightReportPresentation(input).report.overview,
    input.insights[0].fact,
  )
  const empty = prepareInsightReportPresentation(source(true, [])).report
  assert.equal(empty.overview, '원본 근거로 확인할 수 있는 인사이트가 없습니다.')
  assert.equal(empty.validation?.overviewValidated, false)
  const normalized = normalizeInsightReport({
    ...source(true),
    overview: ' ',
    validation: { overviewValidated: true },
  })!
  assert.equal(normalized.validation?.overviewValidated, false)
})

test('근거 배지는 확률처럼 보이는 수치 대신 검증 상태를 표현한다', () => {
  assert.equal(insightValidationLabel('verified'), '원본 근거 확인')
  assert.equal(insightValidationLabel('limited'), '근거 확인 필요')
  assert.equal(insightValidationLabel(null), '근거 정보 없음')
  assert.doesNotMatch(insightValidationLabel('verified'), /\d|%|일치/)
})
