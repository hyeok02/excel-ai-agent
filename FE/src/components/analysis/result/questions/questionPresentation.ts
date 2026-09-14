export const QUESTION_SUGGESTIONS = [
  '이 파일은 무엇을 비교하고 있어?',
  '가장 중요한 수치와 비교 기준은?',
  '이 파일은 어떤 시트로 구성돼 있어?',
] as const

export const questionEvidenceDisclosureLabel = (count: number) =>
  `답변의 원본 근거 ${count}개 보기`
