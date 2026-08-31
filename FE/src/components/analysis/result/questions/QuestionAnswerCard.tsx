import { Bot, CheckCircle2, CircleAlert, ShieldQuestion } from 'lucide-react'

import type { WorkbookQuestionAnswer } from '@/api/analysis'
import QuestionEvidenceList from '@/components/analysis/result/questions/QuestionEvidenceList'

const TOOL_LABELS: Record<string, string> = {
  search_workbook_data: '원본 셀 검색',
  inspect_semantic_structure: '시트 구조 확인',
  trace_formula_dependencies: '수식 참조 추적',
  detect_circular_references: '순환 참조 확인',
  assess_formula_risks: '수식 위험 검사',
}

const STATUS = {
  answered: { label: '근거 확인', icon: CheckCircle2, style: 'bg-emerald-50 text-emerald-700' },
  limited: { label: '일부 범위 확인', icon: CircleAlert, style: 'bg-amber-50 text-amber-700' },
  insufficient_evidence: { label: '근거 부족', icon: ShieldQuestion, style: 'bg-slate-100 text-slate-600' },
} as const

const QuestionAnswerCard = ({ answer }: { answer: WorkbookQuestionAnswer }) => {
  const presentation = STATUS[answer.status]
  const StatusIcon = presentation.icon
  return (
    <article className="rounded-3xl border border-slate-200 bg-slate-50/70 p-4 md:p-5">
      <p className="text-sm font-extrabold text-slate-900">Q. {answer.question}</p>
      <div className="mt-4 flex items-start gap-3">
        <span className="grid size-9 shrink-0 place-items-center rounded-xl bg-brand-600 text-white">
          <Bot aria-hidden="true" size={18} />
        </span>
        <div className="min-w-0 flex-1">
          <div className="flex flex-wrap items-center gap-2">
            <span className={`inline-flex items-center gap-1 rounded-full px-2.5 py-1 text-[11px] font-extrabold ${presentation.style}`}>
              <StatusIcon aria-hidden="true" size={13} /> {presentation.label}
            </span>
            <span className="text-xs font-bold text-slate-400">
              신뢰도 {Math.round(answer.confidence * 100)}%
            </span>
          </div>
          <p className="mt-3 whitespace-pre-wrap text-sm leading-7 text-slate-700">
            {answer.answer}
          </p>
          <div className="mt-3 flex flex-wrap gap-1.5">
            {answer.selectedTools.map((tool) => (
              <span className="rounded-lg bg-white px-2 py-1 text-[11px] font-bold text-slate-500 ring-1 ring-slate-200" key={tool}>
                {TOOL_LABELS[tool] ?? tool}
              </span>
            ))}
          </div>
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
