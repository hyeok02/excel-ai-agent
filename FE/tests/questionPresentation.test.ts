import assert from 'node:assert/strict'
import test from 'node:test'

import {
  buildQuestionSuggestions,
  questionEvidenceDisclosureLabel,
} from '../src/components/analysis/result/questions/questionPresentation.ts'

const report = (titles: string[]) =>
  ({
    overview: '',
    insights: titles.map((title) => ({ title })),
    limitations: [],
    hasIncompleteData: false,
    validation: null,
  }) as never

test('추천 질문을 파일의 인사이트 제목에서 뽑는다', () => {
  const found = buildQuestionSuggestions(
    report(['CVD 장비 점검 현황', '네트워크 안정 표시', 'TCK 작업 표시']),
  )

  assert.deepEqual(found, [
    '이 파일 뭐야?',
    'CVD 장비 점검 알려줘',
    '네트워크 안정 알려줘',
    '이 파일은 어떤 시트로 구성돼 있어?',
  ])
})

test('다른 파일에서는 다른 질문이 나온다', () => {
  const found = buildQuestionSuggestions(report(['전체 직원 수 추이', '부서별 인원 분포']))

  assert.ok(found.includes('전체 직원 수 알려줘'))
  assert.ok(found.includes('부서별 인원 알려줘'))
})

test('분석 결과가 없으면 어떤 파일에나 답할 수 있는 질문만 남는다', () => {
  assert.deepEqual(buildQuestionSuggestions(null), [
    '이 파일 뭐야?',
    '이 파일은 어떤 시트로 구성돼 있어?',
  ])
})

test('접힌 근거의 접근 가능한 이름에 개수를 포함한다', () => {
  assert.equal(questionEvidenceDisclosureLabel(4), '답변의 원본 근거 4개 보기')
})
