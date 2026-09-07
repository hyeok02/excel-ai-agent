import assert from 'node:assert/strict'
import test from 'node:test'

import { getQuestionValidationMessage } from '../src/components/analysis/result/questions/questionValidation.ts'

test('워크북의 고유 용어를 쓴 자연스러운 질문을 통과시킨다', () => {
  assert.equal(getQuestionValidationMessage('DenizBank는 누가 샀어?'), null)
  assert.equal(getQuestionValidationMessage('Nordax는?'), null)
  assert.equal(getQuestionValidationMessage('안녕'), null)
})

test('빈 값과 두 글자 미만의 입력을 차단한다', () => {
  assert.match(getQuestionValidationMessage('  ') ?? '', /두 글자/)
  assert.match(getQuestionValidationMessage('뭐') ?? '', /두 글자/)
})

test('명백한 반복 입력과 자모만 있는 입력을 차단한다', () => {
  assert.match(getQuestionValidationMessage('testtesttest') ?? '', /의미 있는/)
  assert.match(getQuestionValidationMessage('ㅋㅋㅋㅋ') ?? '', /의미 있는/)
  assert.match(getQuestionValidationMessage('ㄴㅇㅁㄹ') ?? '', /의미 있는/)
})
