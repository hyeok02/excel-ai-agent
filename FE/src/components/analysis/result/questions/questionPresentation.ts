import type { InsightReportResult } from '@/api/analysis/insightTypes'

// 어떤 파일이든 답할 수 있는 질문. 분석 결과가 없을 때의 기본값이기도 하다.
const GENERAL_QUESTIONS = ['이 파일 뭐야?', '이 파일은 어떤 시트로 구성돼 있어?']
const MAX_DERIVED = 2
const MAX_SUBJECT_LENGTH = 24
// 제목 끝에 붙는 분류어. 질문으로 읽히게 떼어낸다.
const TITLE_SUFFIXES = ['현황', '표시', '추이', '변화', '분포', '요약']

export const QUESTION_SUGGESTIONS = GENERAL_QUESTIONS

/**
 * 추천 질문을 파일에서 뽑는다.
 *
 * 고정된 세 문장을 모든 파일에 띄우면, 비교 자료가 아닌 파일에도 "무엇을
 * 비교하고 있어?"를 권하게 된다. 그 파일에는 답할 비교가 없으니 어떤 질문을
 * 눌러도 같은 요약이 나온다.
 */
export const buildQuestionSuggestions = (
  report: InsightReportResult | null,
): string[] => {
  const derived: string[] = []
  for (const insight of report?.insights ?? []) {
    const subject = questionSubject(insight.title)
    if (!subject || derived.some((item) => item.includes(subject))) continue
    derived.push(`${subject} 알려줘`)
    if (derived.length >= MAX_DERIVED) break
  }
  return [GENERAL_QUESTIONS[0], ...derived, GENERAL_QUESTIONS[1]]
}

const questionSubject = (title: string): string => {
  let subject = title.trim().replace(/\s*\([^)]*\)\s*$/, '')
  for (const suffix of TITLE_SUFFIXES) {
    if (subject.endsWith(suffix)) subject = subject.slice(0, -suffix.length).trim()
  }
  return subject.length > 1 && subject.length <= MAX_SUBJECT_LENGTH ? subject : ''
}

export const questionEvidenceDisclosureLabel = (count: number) =>
  `답변의 원본 근거 ${count}개 보기`
