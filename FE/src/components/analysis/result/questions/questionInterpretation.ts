import type { WorkbookQuestionAnswer } from '../../../../api/analysis/questionTypes.ts'

/** 원본 전체로 계산했고 남은 문장이 항목 해석뿐이면, 경고가 아니라 해석으로 보여준다. */
export const interpretationOnly = (answer: WorkbookQuestionAnswer) =>
  answer.verification?.level === 'source_checked' &&
  (answer.verification.checks ?? []).includes('field_interpretation') &&
  answer.limitations.length === 1
