import assert from 'node:assert/strict'
import test from 'node:test'

import {
  EVIDENCE_PREVIEW_LIMIT,
  evidenceToggleLabel,
  limitEvidence,
} from '../src/components/analysis/common/evidencePreview.ts'

const items = Array.from({ length: 67 }, (_, index) => index)

test('접힌 상태에서는 앞의 정해진 개수만 보여준다', () => {
  const { visible, hiddenCount } = limitEvidence(items, false)

  assert.equal(visible.length, EVIDENCE_PREVIEW_LIMIT)
  assert.equal(hiddenCount, items.length - EVIDENCE_PREVIEW_LIMIT)
})

test('펼치면 전체를 보여주되 숨겼던 개수는 유지한다', () => {
  const { visible, hiddenCount } = limitEvidence(items, true)

  assert.deepEqual(visible, items)
  assert.equal(hiddenCount, items.length - EVIDENCE_PREVIEW_LIMIT)
})

test('상한보다 적으면 더 보기 버튼이 필요 없다', () => {
  const { visible, hiddenCount } = limitEvidence([1, 2, 3], false)

  assert.deepEqual(visible, [1, 2, 3])
  assert.equal(hiddenCount, 0)
})

test('버튼 문구는 남은 개수와 접기 상태를 모두 알린다', () => {
  assert.equal(evidenceToggleLabel(false, 55), '나머지 55개 더 보기')
  assert.equal(evidenceToggleLabel(true, 55), '근거 접기')
})
