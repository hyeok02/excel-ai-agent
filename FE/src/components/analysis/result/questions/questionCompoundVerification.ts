import type { WorkbookQuestionAnswer } from '../../../../api/analysis/questionTypes.ts'

/** A checked subquestion cannot lend its badge to the whole compound answer. */
export const compoundQuestionVerification = (
  answer: WorkbookQuestionAnswer,
  checks: string[],
) => {
  if (!answer.selectedTools.includes('composite_question')) return null
  const counts = checks.filter((check) => /^compound_parts_[2-4]$/.test(check))
  const count = counts.length === 1 ? Number(counts[0].slice(-1)) : 0
  const citedParts = new Set(
    answer.evidence
      .filter((item) => item.sheetName && item.reference)
      .map((item) => Number(/^문항 ([1-4]) · /u.exec(item.label)?.[1] ?? 0)),
  )
  const allPartsCited =
    count >= 2 &&
    Array.from({ length: count }, (_, i) => i + 1).every((part) => citedParts.has(part))
  const complete =
    answer.status === 'answered' &&
    answer.verification?.level === 'request_checked' &&
    answer.limitations.length === 0 &&
    allPartsCited &&
    ['compound_request_coverage', 'independent_subquestions', 'request_alignment'].every(
      (check) => checks.includes(check),
    )
  if (complete) {
    return {
      label: '문항별 범위·원본 대조',
      tone: 'verified',
      explanation: '각 문항의 조건·계산과 원본 근거를 따로 확인했습니다.',
    } as const
  }
  return {
    label: '복합 질문 · 일부 확인',
    tone: answer.evidence.length ? 'limited' : 'neutral',
    explanation:
      '확인된 문항만 표시합니다. 한 문항의 근거로 전체 답변을 검증한 것은 아닙니다.',
  } as const
}
