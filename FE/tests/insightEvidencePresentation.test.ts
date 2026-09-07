import assert from 'node:assert/strict'
import test from 'node:test'

import {
  insightEvidenceDisclosureLabel,
  parseInsightEvidenceLocation,
  prepareInsightEvidence,
} from '../src/components/analysis/result/insightEvidencePresentation.ts'

const evidence = [
  'Detailed_Headcount_Analytics!B6:D6',
  'Detailed_Headcount_Analytics!E15:L15',
  'Detailed_Headcount_Analytics!E108:L108',
  'Detailed_Headcount_Analytics!E109:L109',
]

test('원본 위치가 많으면 처음 두 개와 숨긴 개수를 제공한다', () => {
  const result = prepareInsightEvidence(evidence, false)
  assert.deepEqual(
    result.visibleLocations.map(({ raw }) => raw),
    evidence.slice(0, 2),
  )
  assert.equal(result.hiddenCount, 2)
})

test('펼치면 전체 위치를 제공하고 중복·빈 위치는 제거한다', () => {
  const result = prepareInsightEvidence([...evidence, evidence[0], '  '], true)
  assert.deepEqual(
    result.visibleLocations.map(({ raw }) => raw),
    evidence,
  )
  assert.equal(result.hiddenCount, 2)
})

test('시트 이름과 셀 범위를 배지용 값으로 분리한다', () => {
  assert.deepEqual(parseInsightEvidenceLocation("'월별 현황'!$B$2:D8"), {
    raw: "'월별 현황'!$B$2:D8",
    sheetName: '월별 현황',
    cellRange: '$B$2:D8',
  })
  assert.deepEqual(parseInsightEvidenceLocation("'대표''자료'!A1"), {
    raw: "'대표''자료'!A1",
    sheetName: "대표'자료",
    cellRange: 'A1',
  })
})

test('셀 주소 형식이 아니면 원문을 보존한다', () => {
  assert.deepEqual(parseInsightEvidenceLocation('원본 위치 미상'), {
    raw: '원본 위치 미상',
    sheetName: null,
    cellRange: null,
  })
})

test('접힌 근거 목록의 접근 가능한 이름에 위치 개수를 포함한다', () => {
  assert.equal(insightEvidenceDisclosureLabel(4), '원본 근거 4개 위치 보기')
})
