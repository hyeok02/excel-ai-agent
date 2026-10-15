import type { InsightReportResult, InsightResult } from '@/api/analysis/insightTypes'

import { prepareInsightReportPresentation } from '../insightReportPresentation.ts'

// 어떤 파일이든 답할 수 있는 질문. 분석 결과가 없을 때의 기본값이기도 하다.
const GENERAL_QUESTIONS = ['이 파일 뭐야?', '이 파일은 어떤 시트로 구성돼 있어?']
const MAX_DERIVED = 2
const MAX_LABEL_LENGTH = 70
const GENERIC_TITLES = /^(?:인사이트\s*\d+|원본(?:에서)?\s*확인한\s*내용)$/
const CHANGE_RESULT_SUFFIX = /\s+-?\d+(?:[.,]\d+)?%\s*(?:증가|감소)$/

export const QUESTION_SUGGESTIONS = GENERAL_QUESTIONS

/**
 * 추천 질문을 검증된 인사이트의 의도에서 뽑는다.
 *
 * 제목에서 `변화`, `분포` 같은 말을 지운 뒤 모두 `알려줘`로 바꾸면 질문이
 * 실제 인사이트보다 모호해진다. 카테고리와 제목의 의미를 질문에 남겨서, 같은
 * 원본 근거를 다시 찾을 수 있는 질문만 제안한다.
 */
export const buildQuestionSuggestions = (
  report: InsightReportResult | null,
): string[] => {
  const derived: string[] = []
  const seen = new Set(GENERAL_QUESTIONS.map(questionKey))

  const visibleInsights = report
    ? prepareInsightReportPresentation(report).report.insights
    : []
  for (const insight of visibleInsights) {
    const question = derivedQuestion(insight)
    const key = questionKey(question)
    if (!question || seen.has(key)) continue

    seen.add(key)
    derived.push(question)
    if (derived.length >= MAX_DERIVED) break
  }

  return [GENERAL_QUESTIONS[0], ...derived, GENERAL_QUESTIONS[1]]
}

const derivedQuestion = (insight: InsightResult): string => {
  const title = usableLabel(insight.title)
  if (!title) return ''

  if (title.endsWith('점검 현황')) {
    return `${stripSuffix(title, '현황')}을 항목별로 요약해줘`
  }
  if (title.endsWith('표시')) {
    return `${stripSuffix(title, '표시')}의 표시별 건수를 요약해줘`
  }
  if (title.endsWith('분포')) {
    return `${title}를 항목별로 요약해줘`
  }
  if (title.endsWith('구성')) {
    return `${title}을 항목별로 요약해줘`
  }

  const topic = usableLabel(insight.topic ?? '')
  switch (insight.category) {
    case 'change': {
      const subject = topic || changeSubject(title)
      return subject ? `${subject} 변화를 시작 값과 마지막 값 기준으로 비교해줘` : ''
    }
    case 'trend': {
      const subject = topic || stripSuffix(title, '추이', '변화')
      return subject ? `${subject}의 기간별 추이를 설명해줘` : ''
    }
    case 'metric':
      return `${title} 관련 수치와 원본 근거를 보여줘`
    case 'risk':
      return `${title}에서 확인된 위험과 원본 근거를 설명해줘`
    case 'formula':
      return `${title}의 수식과 참조 관계를 설명해줘`
    case 'structure':
      return `${title}의 구성을 설명해줘`
    case 'summary':
      return `${title}에 기록된 내용을 원본 근거와 함께 요약해줘`
  }
}

const usableLabel = (value: string): string => {
  const label = value.replace(/\s+/g, ' ').trim()
  if (label.length < 2 || label.length > MAX_LABEL_LENGTH || GENERIC_TITLES.test(label)) {
    return ''
  }
  return label
}

const changeSubject = (title: string) =>
  stripSuffix(title.replace(CHANGE_RESULT_SUFFIX, ''), '변화', '추이')

const stripSuffix = (value: string, ...suffixes: string[]) => {
  for (const suffix of suffixes) {
    if (value.endsWith(suffix)) {
      return value.slice(0, -suffix.length).trim()
    }
  }
  return value
}

const questionKey = (question: string) =>
  question.replace(/[^0-9A-Za-z가-힣]+/g, '').toLocaleLowerCase('ko')

export const questionEvidenceDisclosureLabel = (count: number) =>
  `답변의 원본 근거 ${count}개 보기`
