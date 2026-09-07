import { ChevronDown, ChevronUp } from 'lucide-react'
import { useState } from 'react'

import { prepareInsightEvidence } from '@/components/analysis/result/insightEvidencePresentation'

const InsightEvidenceList = ({ evidence }: { evidence: string[] }) => {
  const [expanded, setExpanded] = useState(false)
  const { visibleLocations, hiddenCount } = prepareInsightEvidence(evidence, expanded)

  return (
    <div className="mt-4">
      <p className="text-xs font-extrabold text-slate-500">내용을 확인한 위치</p>
      <ul className="mt-2 space-y-1.5">
        {visibleLocations.map((location, index) => (
          <li
            className="break-words rounded-xl bg-slate-50 px-3 py-2 text-xs leading-5 text-slate-600"
            key={`${location}-${index}`}
          >
            {location}
          </li>
        ))}
      </ul>
      {hiddenCount > 0 && (
        <button
          aria-expanded={expanded}
          className="mt-2 inline-flex items-center gap-1.5 rounded-lg px-2 py-1.5 text-xs font-extrabold text-slate-500 transition hover:bg-slate-50 hover:text-brand-700"
          onClick={() => setExpanded((current) => !current)}
          type="button"
        >
          {expanded ? (
            <>
              <ChevronUp aria-hidden="true" size={14} /> 위치 접기
            </>
          ) : (
            <>
              <ChevronDown aria-hidden="true" size={14} /> 위치 {hiddenCount}개 더 보기
            </>
          )}
        </button>
      )}
    </div>
  )
}

export default InsightEvidenceList
