import assert from 'node:assert/strict'
import test from 'node:test'

import type {
  WorkbookWriteback,
  WritebackChange,
} from '../src/api/analysis/writebackTypes.ts'
import {
  allChangeKeys,
  appliedChangeKeys,
  appliedSummary,
} from '../src/components/analysis/result/writeback/writebackSelection.ts'

const change = (reference: string): WritebackChange => ({
  newValue: 2,
  oldValue: 1,
  reason: '요청',
  reference,
  sheetName: '매출',
})

test('일부만 승인해 적용했으면 적용한 개수와 원본 그대로인 개수를 알린다', () => {
  const changes = [change('H4'), change('H5'), change('H6')]
  const item = {
    status: 'APPLIED',
    verification: { changedCells: ['매출!H4', '매출!H6'], checks: [], verified: true },
  } as unknown as WorkbookWriteback
  const applied = appliedChangeKeys(item)!
  assert.equal(applied.has('매출!H5'), false)
  assert.equal(
    appliedSummary(changes, applied),
    '제안한 3개 중 승인한 2개 셀을 수정본에 적용했습니다. 나머지 1개는 원본 그대로입니다.',
  )
  assert.equal(
    appliedSummary(changes, new Set(allChangeKeys(changes))),
    '승인한 3개 셀을 수정본에 적용했습니다.',
  )
  assert.equal(appliedChangeKeys({ ...item, status: 'PROPOSED' }), null)
})
