import { ChevronDown, ChevronUp, FileSearch } from 'lucide-react'
import { useState } from 'react'

import type { WorkbookQuestionEvidence } from '@/api/analysis'
import ResponsiveCardColumns from '@/components/analysis/common/ResponsiveCardColumns'
import QuestionEvidenceCard from '@/components/analysis/result/questions/QuestionEvidenceCard'

const INITIAL_EVIDENCE_COUNT = 4

const QuestionEvidenceList = ({ evidence }: { evidence: WorkbookQuestionEvidence[] }) => {
  const [showAll, setShowAll] = useState(false)
  const [expandedFormulaKey, setExpandedFormulaKey] = useState<string | null>(null)

  if (evidence.length === 0) return null

  const visibleEvidence = showAll ? evidence : evidence.slice(0, INITIAL_EVIDENCE_COUNT)
  const hiddenCount = evidence.length - INITIAL_EVIDENCE_COUNT
  const evidenceKey = (item: WorkbookQuestionEvidence) =>
    `${item.sheetName}-${item.reference}`

  return (
    <div className="mt-4">
      <p className="flex items-center gap-2 text-xs font-extrabold text-slate-500">
        <FileSearch aria-hidden="true" size={15} /> 답변을 확인한 원본 위치
      </p>
      <ResponsiveCardColumns
        breakpoint="md"
        className="mt-2"
        density="compact"
        getKey={evidenceKey}
        items={visibleEvidence}
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
      {hiddenCount > 0 && (
        <div className="mt-3 flex justify-center">
          <button
            className="inline-flex items-center gap-1.5 rounded-xl border border-slate-200 bg-white px-3 py-2 text-xs font-extrabold text-slate-600 transition hover:border-brand-200 hover:text-brand-700"
            onClick={() => {
              setShowAll((current) => !current)
              setExpandedFormulaKey(null)
            }}
            type="button"
          >
            {showAll ? (
              <>
                <ChevronUp aria-hidden="true" size={14} /> 근거 접기
              </>
            ) : (
              <>
                <ChevronDown aria-hidden="true" size={14} /> 근거 {hiddenCount}개 더 보기
              </>
            )}
          </button>
        </div>
      )}
    </div>
  )
}

export default QuestionEvidenceList
