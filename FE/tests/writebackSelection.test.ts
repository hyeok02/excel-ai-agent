import assert from 'node:assert/strict'
import test from 'node:test'

import type { WritebackChange } from '../src/api/analysis/writebackTypes.ts'
import {
  allChangeKeys,
  approvalButtonLabel,
  brokenDependencies,
  changeKey,
  toggleChangeKey,
} from '../src/components/analysis/result/writeback/writebackSelection.ts'

const change = (
  reference: string,
  affectedCells: string[] = [],
  sheetName = '매출',
): WritebackChange => ({
  affectedCells,
  newValue: 2,
  oldValue: 1,
  reason: '요청',
  reference,
  sheetName,
})

test('키는 근거 셀 목록과 같은 시트!셀 형식을 쓴다', () => {
  assert.equal(changeKey(change('B12')), '매출!B12')
  assert.deepEqual(allChangeKeys([change('B12'), change('C12')]), [
    '매출!B12',
    '매출!C12',
  ])
})

test('토글은 선택을 켜고 끈다', () => {
  assert.deepEqual(toggleChangeKey(['매출!B12'], '매출!C12'), ['매출!B12', '매출!C12'])
  assert.deepEqual(toggleChangeKey(['매출!B12', '매출!C12'], '매출!B12'), ['매출!C12'])
})

test('전체를 선택하면 의존이 끊기지 않는다', () => {
  const changes = [change('B12', ['매출!C12']), change('C12')]

  assert.deepEqual(brokenDependencies(changes, allChangeKeys(changes)), [])
  assert.deepEqual(brokenDependencies(changes, []), [])
})

test('참조하는 쪽만 빼면 참조된 쪽이 미리보기와 달라진다', () => {
  const changes = [change('B12', ['매출!C12']), change('C12')]

  assert.deepEqual(brokenDependencies(changes, ['매출!B12']), ['매출!C12'])
  assert.deepEqual(brokenDependencies(changes, ['매출!C12']), ['매출!B12'])
})

test('제안에 없는 셀을 참조해도 경고하지 않는다', () => {
  const changes = [change('B12', ['매출!Z99'])]

  assert.deepEqual(brokenDependencies(changes, ['매출!B12']), [])
})

test('버튼 문구는 일부만 골랐을 때 개수를 알린다', () => {
  assert.equal(approvalButtonLabel(3, 3), '승인하고 수정본 만들기')
  assert.equal(approvalButtonLabel(2, 3), '선택한 2개만 승인하고 수정본 만들기')
})
