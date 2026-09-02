import { ChevronDown, ChevronUp } from 'lucide-react'
import { useId } from 'react'

import type { WorkbookQuestionEvidence } from '@/api/analysis'
import OriginalLocationButton from '@/components/analysis/workbook/details/OriginalLocationButton'

interface QuestionEvidenceCardProps {
  expanded: boolean
  item: WorkbookQuestionEvidence
  onFormulaToggle: () => void
}

const QuestionEvidenceCard = ({
  expanded,
  item,
  onFormulaToggle,
}: QuestionEvidenceCardProps) => {
  const formulaId = useId()

  return (
    <div className="rounded-2xl border border-slate-200 bg-white p-3">
      <div className="flex flex-wrap items-start justify-between gap-2">
        <div className="min-w-0 flex-1">
          <p className="truncate text-xs font-extrabold text-brand-700">
            {item.sheetName}!{item.reference}
          </p>
          <p className="mt-1 line-clamp-2 min-h-10 break-words text-sm font-semibold leading-5 text-slate-700">
            {item.label}
          </p>
        </div>
        <div className="flex shrink-0 flex-wrap items-center justify-end gap-1.5">
          {item.formula && (
            <button
              aria-controls={formulaId}
              aria-expanded={expanded}
              className="inline-flex items-center gap-1 rounded-lg border border-slate-200 bg-white px-2.5 py-2 text-xs font-bold text-slate-600 transition hover:border-brand-200 hover:text-brand-700"
              onClick={onFormulaToggle}
              type="button"
            >
              {expanded ? (
                <ChevronUp aria-hidden="true" size={14} />
              ) : (
                <ChevronDown aria-hidden="true" size={14} />
              )}
              {expanded ? '수식 접기' : '수식 보기'}
            </button>
          )}
          <OriginalLocationButton location={item.reference} sheetName={item.sheetName} />
        </div>
      </div>
      {item.formula && expanded && (
        <code
          className="mt-2 block overflow-x-auto rounded-lg bg-slate-50 px-2 py-1.5 text-[11px] text-slate-500"
          id={formulaId}
        >
          {item.formula}
        </code>
      )}
    </div>
  )
}

export default QuestionEvidenceCard
