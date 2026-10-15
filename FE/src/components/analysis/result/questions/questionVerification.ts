import type { WorkbookQuestionAnswer } from '../../../../api/analysis/questionTypes.ts'

/** Answer availability and source citations are not a correctness certificate. */
export const questionVerificationPresentation = (answer: WorkbookQuestionAnswer) => {
  if (answer.status === 'insufficient_evidence') {
    if (answer.selectedTools.includes('clarify_source_scope')) {
      return {
        label: '대상 확인 필요',
        tone: 'neutral',
        explanation: '후보 중 원하는 원본 범위를 지정하면 이어서 조회할 수 있습니다.',
      } as const
    }
    return { label: '답변 검증 불가', tone: 'neutral', explanation: '' } as const
  }
  const verification = answer.verification
  const checks = Array.isArray(verification?.checks) ? verification.checks : []
  if (checks.includes('bounded_recalculation')) {
    return {
      label: '수식 재계산',
      tone: 'limited',
      explanation:
        '파일 내부 입력으로 다시 계산한 값입니다. Excel이나 외부 서비스의 최신 저장값을 확인한 것은 아닙니다.',
    } as const
  }
  if (
    verification?.level === 'source_checked' &&
    ['cited_cells', 'header_labels', 'header_positions'].every((check) =>
      checks.includes(check),
    )
  ) {
    return {
      label: '항목 구조 확인',
      tone: 'limited',
      explanation:
        '원본 열 이름과 배치를 확인했습니다. 실제 의미나 작업 내용의 동일 여부를 확인한 것은 아닙니다.',
    } as const
  }
  const requestChecksComplete =
    checks.includes('table_scope') &&
    (checks.includes('source_values') || checks.includes('source_cells')) &&
    (checks.includes('request_alignment') || checks.includes('metric'))
  if (
    verification?.level === 'request_checked' &&
    requestChecksComplete &&
    answer.status === 'answered'
  ) {
    return {
      label: '질문 범위·원본 대조',
      tone: 'verified',
      explanation: '선택한 표·항목·조건과 원본 값을 대조한 결과입니다.',
    } as const
  }
  if (answer.status === 'limited') {
    return {
      label: '일부 범위만 대조',
      tone: 'limited',
      explanation:
        '아래 확인 한계를 확인해 주세요. 전체 답변의 정확성을 보장하지 않습니다.',
    } as const
  }
  if (verification?.level === 'source_checked') {
    return {
      label: '인용 원본 대조',
      tone: 'neutral',
      explanation:
        '인용한 셀과 답변을 대조했습니다. 질문 범위 전체를 검증한 것은 아닙니다.',
    } as const
  }
  return {
    label: '원본 근거 제공',
    tone: 'neutral',
    explanation: '원본 근거를 제공합니다. 질문 범위와 답변을 별도로 확인해 주세요.',
  } as const
}
