import assert from 'node:assert/strict'
import test from 'node:test'

import type { InsightResult } from '../src/api/analysis/insightTypes.ts'
import { groupInsights } from '../src/components/analysis/result/insightGroupPresentation.ts'
import { prepareInsightReportPresentation } from '../src/components/analysis/result/insightReportPresentation.ts'

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

test('원본 열 이름 주제 하나뿐인 섹션은 한국어 카드 제목을 제목으로 쓴다', () => {
  const groups = groupInsights([
    insight({ category: 'metric', topic: 'TotalPrice', title: '식품 판매금액 합계' }),
    insight({
      category: 'summary',
      topic: 'InsuredValue',
      title: '지역(State)별 보험가액 비중',
    }),
  ])
  assert.deepEqual(
    groups.map(({ title }) => title),
    ['식품 판매금액 합계', '지역(State)별 보험가액 비중'],
  )
  const korean = groupInsights([
    insight({ category: 'trend', topic: '전체 직원 수', title: '전체 직원 수 변화' }),
  ])
  assert.equal(korean[0].title, '전체 직원 수 추이')
})

test('카드마다 되풀이되던 파일 소개 문장은 한눈에 보기에만 남긴다', () => {
  const lead = '이 파일은 식품 판매 내역 244건을 정리한 예시 자료입니다.'
  const { report } = prepareInsightReportPresentation({
    overview: `${lead} 판매금액 합계는 $33,325.58입니다.`,
    insights: [
      insight({ category: 'metric', fact: `${lead}\n판매금액 합계는 $33,325.58입니다.` }),
      insight({ fact: '분류별로 보면 Cookies가 가장 큽니다.' }),
      insight({ fact: lead }),
    ],
    limitations: [],
    hasIncompleteData: false,
    validation: {
      generatedCount: 3,
      verifiedCount: 3,
      limitedCount: 0,
      blockedCount: 0,
      notices: [],
      overviewValidated: true,
    },
  })
  assert.deepEqual(
    report.insights.map(({ fact }) => fact),
    ['판매금액 합계는 $33,325.58입니다.', '분류별로 보면 Cookies가 가장 큽니다.', lead],
  )
})
