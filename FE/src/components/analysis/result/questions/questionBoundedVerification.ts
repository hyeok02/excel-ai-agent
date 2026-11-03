import type { WorkbookQuestionAnswer } from '../../../../api/analysis/questionTypes.ts'

/** A model-selected label or corrected premise is never a request-level proof. */
export const boundedQuestionVerification = (
  answer: WorkbookQuestionAnswer,
  checks: string[],
) => {
  const sourceChecked =
    answer.verification?.level === 'source_checked' ||
    answer.verification?.level === 'request_checked'
  if (checks.includes('rank_interpretation')) {
    return {
      label: sourceChecked ? '해석 후 원본 대조' : '순위 해석 확인 필요',
      tone: sourceChecked ? 'limited' : 'neutral',
      explanation: sourceChecked
        ? '질문의 대상명과 순위 기준(집계 항목·방식)을 해석한 뒤 원본 값을 대조했습니다. 위의 해석한 질문이 의도와 맞는지 확인해 주세요.'
        : '질문의 대상명과 순위 기준을 해석했지만 원본 대조를 완료하지 못했습니다. 해석한 질문과 확인 한계를 확인해 주세요.',
    } as const
  }
  if (checks.includes('semantic_alias_resolved')) {
    return {
      label: sourceChecked ? '대상 해석 · 원본 확인' : '대상 해석 확인 필요',
      tone: sourceChecked ? 'limited' : 'neutral',
      explanation:
        '질문의 대상명을 원본 이름으로 해석한 결과입니다. 두 이름이 같은 대상을 뜻하는지 확인해 주세요.',
    } as const
  }
  if (checks.includes('premise_not_confirmed')) {
    return {
      label: sourceChecked ? '원본 조회 · 전제 미확인' : '전제 확인 필요',
      tone: sourceChecked ? 'limited' : 'neutral',
      explanation:
        '원본 값을 조회한 결과이며, 질문에 제시한 수치나 전제가 맞다고 확인한 것은 아닙니다.',
    } as const
  }
  if (checks.includes('category_match_interpreted')) {
    return {
      label: sourceChecked ? '조건 해석 · 원본 확인' : '조건 해석 확인 필요',
      tone: sourceChecked ? 'limited' : 'neutral',
      explanation:
        '입력한 범주를 설명이 붙은 원본 값에 연결했습니다. 표시된 검색 조건이 의도와 맞는지 확인해 주세요.',
    } as const
  }
  return null
}
