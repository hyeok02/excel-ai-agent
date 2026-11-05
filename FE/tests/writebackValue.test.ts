import assert from 'node:assert/strict'
import test from 'node:test'

import { showValue } from '../src/components/analysis/result/writeback/writebackValue.ts'

test('셀 서식대로 보이는 값이 있으면 저장된 숫자 대신 그것을 보여준다', () => {
  assert.equal(showValue(0.0328938320114756, '3.3%'), '3.3%')
  assert.equal(showValue(0.013, '1.3%'), '1.3%')
})

test('서식 값이 없으면 원래 값을 그대로 보여준다', () => {
  assert.equal(showValue(0.013), '0.013')
  assert.equal(showValue('Cookies', null), 'Cookies')
  assert.equal(showValue(null), '(빈 셀)')
  assert.equal(showValue(true), 'TRUE')
})
