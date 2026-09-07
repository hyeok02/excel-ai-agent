import assert from 'node:assert/strict'
import test from 'node:test'

import { prepareInsightEvidence } from '../src/components/analysis/result/insightEvidencePresentation.ts'

const evidence = [
  'Detailed_Headcount_Analytics!B6:D6',
  'Detailed_Headcount_Analytics!E15:L15',
  'Detailed_Headcount_Analytics!E108:L108',
  'Detailed_Headcount_Analytics!E109:L109',
]

test('원본 위치가 많으면 처음 두 개와 숨긴 개수를 제공한다', () => {
  assert.deepEqual(prepareInsightEvidence(evidence, false), {
    visibleLocations: evidence.slice(0, 2),
    hiddenCount: 2,
  })
})

test('펼치면 전체 위치를 제공하고 중복·빈 위치는 제거한다', () => {
  const result = prepareInsightEvidence([...evidence, evidence[0], '  '], true)
  assert.deepEqual(result.visibleLocations, evidence)
  assert.equal(result.hiddenCount, 2)
})
