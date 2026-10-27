import type { WorkbookQuestionAnswer } from '../../../../api/analysis/questionTypes.ts'
import { boundedQuestionVerification } from './questionBoundedVerification.ts'
import { composedQuestionVerification } from './questionComposedVerification.ts'
import { compoundQuestionVerification } from './questionCompoundVerification.ts'
import { requestQuestionVerification } from './questionRequestVerification.ts'

/** Answer availability and source citations are not a correctness certificate. */
export const questionVerificationPresentation = (answer: WorkbookQuestionAnswer) => {
  const verification = answer.verification
  const checks = Array.isArray(verification?.checks) ? verification.checks : []
  if (answer.status === 'insufficient_evidence') {
    if (answer.selectedTools.includes('clarify_question_context')) {
      return {
        label: '질문 맥락 확인 필요',
        tone: 'neutral',
        explanation:
          '어떤 항목이나 앞선 질문을 가리키는지 알려주시면 원본을 다시 확인합니다.',
      } as const
    }
    if (answer.selectedTools.includes('clarify_source_scope')) {
      return {
        label: '대상 확인 필요',
        tone: 'neutral',
        explanation: '후보 중 원하는 원본 범위를 지정하면 이어서 조회할 수 있습니다.',
      } as const
    }
    if (checks.includes('interpretation_unverified')) {
      return {
        label: '의미 확인 필요',
        tone: 'neutral',
        explanation:
          '원본 표시의 업무상 의미나 원인을 입증할 근거를 확인하지 못했습니다.',
      } as const
    }
    return { label: '답변 검증 불가', tone: 'neutral', explanation: '' } as const
  }
  const compound = compoundQuestionVerification(answer, checks)
  if (compound) return compound
  if (checks.includes('bounded_recalculation')) {
    return {
      label: '수식 재계산',
      tone: 'limited',
      explanation:
        '파일 내부 입력으로 다시 계산한 값입니다. Excel이나 외부 서비스의 최신 저장값을 확인한 것은 아닙니다.',
    } as const
  }
  const bounded = boundedQuestionVerification(answer, checks)
  if (bounded) return bounded
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
  if (checks.includes('context_resolved')) {
    const sourceChecked =
      verification?.level === 'source_checked' ||
      verification?.level === 'request_checked'
    return {
      label: sourceChecked ? '맥락 연결 · 원본 확인' : '맥락 연결 · 근거 확인 필요',
      tone: sourceChecked ? 'limited' : 'neutral',
      explanation: sourceChecked
        ? '앞선 맥락에서 대상을 해석한 뒤 원본 값을 다시 확인했습니다. 위의 해석한 질문이 의도한 대상과 맞는지 확인해 주세요.'
        : '앞선 맥락에서 대상을 해석했지만 원본 근거 확인은 완료하지 못했습니다. 해석한 질문과 아래 확인 한계를 확인해 주세요.',
    } as const
  }
  if (checks.includes('interpretation_unverified')) {
    const sourceChecked =
      verification?.level === 'source_checked' ||
      verification?.level === 'request_checked'
    return {
      label: sourceChecked ? '원본 확인 · 의미 미확인' : '의미 확인 필요',
      tone: sourceChecked ? 'limited' : 'neutral',
      explanation: sourceChecked
        ? '원본 값은 확인했지만, 그 표시의 업무상 의미나 원인까지 입증한 것은 아닙니다.'
        : '원본 표시의 업무상 의미나 원인을 입증할 근거를 확인하지 못했습니다.',
    } as const
  }
  if (
    verification?.level === 'source_checked' &&
    ['cited_cells', 'source_values', 'claim_bindings', 'claim_semantics'].every((check) =>
      checks.includes(check),
    )
  ) {
    return {
      label: '주장별 원본 대조',
      tone: answer.status === 'limited' ? 'limited' : 'neutral',
      explanation:
        '각 주장의 값·대상·기간·항목을 원본 셀과 연결해 확인했습니다. 업무상 의미나 원인까지 입증한 것은 아닙니다.',
    } as const
  }
  const composed = composedQuestionVerification(answer, checks)
  if (composed) return composed
  const request = requestQuestionVerification(answer, checks)
  if (request) return request
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
