import { Bot, CheckCircle2, CircleAlert, ShieldQuestion } from 'lucide-react'

import type { WorkbookQuestionAnswer } from '@/api/analysis'
import QuestionEvidenceList from '@/components/analysis/result/questions/QuestionEvidenceList'
import { questionVerificationPresentation } from '@/components/analysis/result/questions/questionVerification'

const TOOL_LABELS: Record<string, string> = {
  search_workbook_data: '원본 셀 검색',
  inspect_header_relation: '원본 열 이름과 배치 확인',
  tabular_query: '원본 표 범위 대조·집계',
  relational_query: '표 간 연결·원본 대조',
  clarify_source_scope: '모호한 원본 항목 확인',
  recover_formula_values: '원본 입력으로 수식 재계산',
  inspect_missing_formula_inputs: '누락된 수식 입력 확인',
  bind_metric_observations: '지표·기간·단위 원본 대조',
  inspect_semantic_structure: '시트 구조 확인',
  trace_formula_dependencies: '수식 참조 추적',
  detect_circular_references: '순환 참조 확인',
  assess_formula_risks: '수식 위험 검사',
}

const TONE = {
  verified: {
    icon: CheckCircle2,
    style: 'bg-emerald-50 text-emerald-700',
  },
  limited: {
    icon: CircleAlert,
    style: 'bg-amber-50 text-amber-700',
  },
  neutral: {
    icon: ShieldQuestion,
    style: 'bg-slate-100 text-slate-600',
  },
} as const

const QuestionAnswerCard = ({ answer }: { answer: WorkbookQuestionAnswer }) => {
  const hasScopeLimit = answer.limitations.some((message) =>
    message.includes('검색 범위에서 제외'),
  )
  const presentation = questionVerificationPresentation(answer)
  const tone = TONE[presentation.tone]
  const StatusIcon = tone.icon
  return (
    <article className="rounded-3xl border border-slate-200 bg-slate-50/70 p-4 md:p-5">
      <p className="text-sm font-extrabold text-slate-900">Q. {answer.question}</p>
      <div className="mt-4 flex items-start gap-3">
        <span className="grid size-9 shrink-0 place-items-center rounded-xl bg-brand-600 text-white">
          <Bot aria-hidden="true" size={18} />
        </span>
        <div className="min-w-0 flex-1">
          <div className="flex flex-wrap items-center gap-2">
            <span
              className={`inline-flex items-center gap-1 rounded-full px-2.5 py-1 text-[11px] font-extrabold ${tone.style}`}
              title={presentation.explanation}
            >
              <StatusIcon aria-hidden="true" size={13} /> {presentation.label}
            </span>
            {hasScopeLimit && (
              <span className="rounded-full bg-slate-100 px-2.5 py-1 text-[11px] font-bold text-slate-500">
                일부 범위 제외
              </span>
            )}
          </div>
          {presentation.explanation && (
            <p className="mt-2 text-[11px] leading-5 text-slate-500">
              {presentation.explanation}
            </p>
          )}
          <p className="mt-3 whitespace-pre-wrap text-sm leading-7 text-slate-700">
            {answer.answer}
          </p>
          {answer.selectedTools.length > 0 && (
            <details className="mt-3 text-xs text-slate-400">
              <summary className="cursor-pointer font-bold">확인 방법 보기</summary>
              <p className="mt-1">
                {answer.selectedTools
                  .map((tool) => TOOL_LABELS[tool] ?? tool)
                  .join(' · ')}
              </p>
            </details>
          )}
        </div>
      </div>
      <QuestionEvidenceList evidence={answer.evidence} />
      {answer.limitations.length > 0 && (
        <div className="mt-3 rounded-2xl bg-amber-50 px-3 py-2 text-xs leading-5 text-amber-800">
          <strong>확인 한계:</strong> {answer.limitations.join(' ')}
        </div>
      )}
    </article>
  )
}

export default QuestionAnswerCard
