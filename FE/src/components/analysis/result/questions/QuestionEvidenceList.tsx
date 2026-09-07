import { ChevronDown, FileSearch } from 'lucide-react'
import { useState } from 'react'

import type { WorkbookQuestionEvidence } from '@/api/analysis'
import ResponsiveCardColumns from '@/components/analysis/common/ResponsiveCardColumns'
import QuestionEvidenceCard from '@/components/analysis/result/questions/QuestionEvidenceCard'
import { questionEvidenceDisclosureLabel } from '@/components/analysis/result/questions/questionPresentation'

const QuestionEvidenceList = ({ evidence }: { evidence: WorkbookQuestionEvidence[] }) => {
  const [expandedFormulaKey, setExpandedFormulaKey] = useState<string | null>(null)

  if (evidence.length === 0) return null

  const evidenceKey = (item: WorkbookQuestionEvidence) =>
    `${item.sheetName}-${item.reference}`

  return (
    <details className="group mt-4 border-t border-slate-200 pt-3">
      <summary
        aria-label={questionEvidenceDisclosureLabel(evidence.length)}
        className="inline-flex cursor-pointer list-none items-center gap-1.5 rounded-md text-xs font-semibold text-slate-500 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-400 focus-visible:ring-offset-2"
      >
        <FileSearch aria-hidden="true" size={14} /> 원본 근거 · {evidence.length}개
        <ChevronDown
          aria-hidden="true"
          className="transition-transform group-open:rotate-180"
          size={13}
        />
      </summary>
      <ResponsiveCardColumns
        breakpoint="md"
        className="mt-3"
        density="compact"
        getKey={evidenceKey}
        items={evidence}
        renderItem={(item) => {
          const key = evidenceKey(item)
          return (
            <QuestionEvidenceCard
              expanded={expandedFormulaKey === key}
              item={item}
              onFormulaToggle={() =>
                setExpandedFormulaKey((current) => (current === key ? null : key))
              }
            />
          )
        }}
      />
    </details>
  )
}

export default QuestionEvidenceList
