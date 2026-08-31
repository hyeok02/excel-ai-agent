import { FileSearch } from 'lucide-react'

import type { WorkbookQuestionEvidence } from '@/api/analysis'
import OriginalLocationButton from '@/components/analysis/workbook/details/OriginalLocationButton'

const QuestionEvidenceList = ({ evidence }: { evidence: WorkbookQuestionEvidence[] }) => {
  if (evidence.length === 0) return null

  return (
    <div className="mt-4">
      <p className="flex items-center gap-2 text-xs font-extrabold text-slate-500">
        <FileSearch aria-hidden="true" size={15} /> 답변을 확인한 원본 위치
      </p>
      <div className="mt-2 grid gap-2 md:grid-cols-2">
        {evidence.map((item) => (
          <div
            className="rounded-2xl border border-slate-200 bg-white p-3"
            key={`${item.sheetName}-${item.reference}`}
          >
            <div className="flex flex-wrap items-start justify-between gap-2">
              <div className="min-w-0">
                <p className="truncate text-xs font-extrabold text-brand-700">
                  {item.sheetName}!{item.reference}
                </p>
                <p className="mt-1 break-words text-sm font-semibold text-slate-700">
                  {item.label}
                </p>
              </div>
              <OriginalLocationButton
                location={item.reference}
                sheetName={item.sheetName}
              />
            </div>
            {item.formula && (
              <code className="mt-2 block overflow-x-auto rounded-lg bg-slate-50 px-2 py-1.5 text-[11px] text-slate-500">
                {item.formula}
              </code>
            )}
          </div>
        ))}
      </div>
    </div>
  )
}

export default QuestionEvidenceList
