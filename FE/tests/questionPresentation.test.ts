import assert from 'node:assert/strict'
import test from 'node:test'

import type {
  InsightCategory,
  InsightReportResult,
  InsightResult,
} from '../src/api/analysis/insightTypes.ts'
import {
  buildQuestionSuggestions,
  questionEvidenceDisclosureLabel,
} from '../src/components/analysis/result/questions/questionPresentation.ts'

const insight = (
  title: string,
  category: InsightCategory = 'summary',
  topic: string | null = null,
): InsightResult => ({
  title,
  topic,
  category,
  fact: `${title} 사실`,
  cause: null,
  impact: null,
  severity: 'info',
  evidence: ['Sheet1!A1'],
  recommendation: null,
  confidence: 1,
  isIncomplete: false,
  validationStatus: 'verified',
  validationReasons: [],
})

const report = (insights: InsightResult[]): InsightReportResult =>
  ({
    overview: '',
    insights,
    limitations: [],
    hasIncompleteData: false,
    validation: null,
  }) as InsightReportResult

test('점검표 추천 질문은 점검과 표시의 집계 의도를 보존한다', () => {
  const found = buildQuestionSuggestions(
    report([
      insight('CVD 장비 점검 현황'),
      insight('네트워크 안정 표시'),
      insight('TCK 작업 표시'),
    ]),
  )

  assert.deepEqual(found, [
    '이 파일 뭐야?',
    'CVD 장비 점검을 항목별로 요약해줘',
    '네트워크 안정의 표시별 건수를 요약해줘',
    '이 파일은 어떤 시트로 구성돼 있어?',
  ])
})

test('변화 인사이트는 주제와 비교 의도를 질문에 유지한다', () => {
  const found = buildQuestionSuggestions(
    report([
      insight(
        '부서 등 항목별 전체 직원 수 변화',
        'change',
        '부서 등 항목별 전체 직원 수',
      ),
    ]),
  )

  assert.ok(
    found.includes(
      '부서 등 항목별 전체 직원 수 변화를 시작 값과 마지막 값 기준으로 비교해줘',
    ),
  )
  assert.ok(!found.includes('부서 등 항목별 전체 직원 수 알려줘'))
})

test('추이와 분포 인사이트에 서로 다른 답변 의도를 붙인다', () => {
  const found = buildQuestionSuggestions(
    report([
      insight('전체 직원 수 추이', 'trend', '전체 직원 수'),
      insight('부서별 인원 분포'),
    ]),
  )

  assert.ok(found.includes('전체 직원 수의 기간별 추이를 설명해줘'))
  assert.ok(found.includes('부서별 인원 분포를 항목별로 요약해줘'))
})

test('같은 질문만 제거하고 이름이 겹치는 서로 다른 주제는 유지한다', () => {
  const found = buildQuestionSuggestions(
    report([
      insight('전체 직원 수 변화', 'change', '전체 직원 수'),
      insight('전체 직원 수 증감', 'change', '전체 직원 수'),
      insight('직원 수 변화', 'change', '직원 수'),
    ]),
  )

  assert.deepEqual(found, [
    '이 파일 뭐야?',
    '전체 직원 수 변화를 시작 값과 마지막 값 기준으로 비교해줘',
    '직원 수 변화를 시작 값과 마지막 값 기준으로 비교해줘',
    '이 파일은 어떤 시트로 구성돼 있어?',
  ])
})

test('분석 결과가 없거나 제목이 일반적이면 범용 질문만 남는다', () => {
  assert.deepEqual(buildQuestionSuggestions(null), [
    '이 파일 뭐야?',
    '이 파일은 어떤 시트로 구성돼 있어?',
  ])
  assert.deepEqual(buildQuestionSuggestions(report([insight('원본에서 확인한 내용')])), [
    '이 파일 뭐야?',
    '이 파일은 어떤 시트로 구성돼 있어?',
  ])
})

test('화면에서 숨기는 미검증 인사이트는 추천 질문에도 쓰지 않는다', () => {
  const hidden = {
    ...insight('검증되지 않은 매출 변화', 'change', '매출'),
    validationStatus: 'limited' as const,
    validationReasons: ['수치와 원본 근거가 일치하지 않습니다.'],
  }

  assert.deepEqual(buildQuestionSuggestions(report([hidden])), [
    '이 파일 뭐야?',
    '이 파일은 어떤 시트로 구성돼 있어?',
  ])
})

test('접힌 근거의 접근 가능한 이름에 개수를 포함한다', () => {
  assert.equal(questionEvidenceDisclosureLabel(4), '답변의 원본 근거 4개 보기')
})
