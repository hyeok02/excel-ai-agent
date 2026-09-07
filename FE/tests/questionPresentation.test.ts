import assert from 'node:assert/strict'
import test from 'node:test'

import {
  QUESTION_SUGGESTIONS,
  questionEvidenceDisclosureLabel,
} from '../src/components/analysis/result/questions/questionPresentation.ts'

test('추천 질문은 파일의 의미·비교·근거를 묻는다', () => {
  assert.equal(QUESTION_SUGGESTIONS.length, 3)
  assert.match(QUESTION_SUGGESTIONS.join(' '), /무엇을 비교/)
  assert.match(QUESTION_SUGGESTIONS.join(' '), /비교 기준/)
  assert.match(QUESTION_SUGGESTIONS.join(' '), /근거/)
})

test('접힌 근거의 접근 가능한 이름에 개수를 포함한다', () => {
  assert.equal(questionEvidenceDisclosureLabel(4), '답변의 원본 근거 4개 보기')
})
