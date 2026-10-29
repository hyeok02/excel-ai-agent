import assert from 'node:assert/strict'
import test from 'node:test'

import type {
  InsightReportResult,
  InsightResult,
} from '../src/api/analysis/insightTypes.ts'
import { buildQuestionSuggestions } from '../src/components/analysis/result/questions/questionPresentation.ts'

const insight = (title: string, evidence: string[]): InsightResult => ({
  title,
  topic: null,
  category: 'summary',
  fact: `${title} 사실`,
  cause: null,
  impact: null,
  severity: 'info',
  evidence,
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

test('근거 셀이 같은 인사이트는 이름이 달라도 추천 질문을 하나만 만든다', () => {
  const cells = ["'Key_Developments'!E5", "'Key_Developments'!E7:E24"]
  const found = buildQuestionSuggestions(
    report([
      insight('주요 사건 구성', cells),
      insight('사건 유형 분포', [...cells].reverse()),
      insight('사건 발생일 분포', ["'Key_Developments'!C7:C24"]),
    ]),
  )

  assert.deepEqual(found, [
    '이 파일 뭐야?',
    '주요 사건 구성을 항목별로 요약해줘',
    '사건 발생일 분포를 항목별로 요약해줘',
    '이 파일은 어떤 시트로 구성돼 있어?',
  ])
})

test('근거가 일부만 겹치는 인사이트는 각각 추천한다', () => {
  const found = buildQuestionSuggestions(
    report([
      insight('매출 구성', ['Summary!B51', 'Summary!B88']),
      insight('순이익 구성', ['Summary!B51', 'Summary!B143']),
    ]),
  )

  assert.deepEqual(found.slice(1, 3), [
    '매출 구성을 항목별로 요약해줘',
    '순이익 구성을 항목별로 요약해줘',
  ])
})
