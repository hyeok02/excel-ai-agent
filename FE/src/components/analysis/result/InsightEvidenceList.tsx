import { ChevronDown } from 'lucide-react'

import {
  insightEvidenceDisclosureLabel,
  prepareInsightEvidence,
} from '@/components/analysis/result/insightEvidencePresentation'

const InsightEvidenceList = ({ evidence }: { evidence: string[] }) => {
  const { visibleLocations } = prepareInsightEvidence(evidence, true)

  if (visibleLocations.length === 0) return null

  return (
    <details className="group mt-4 border-t border-slate-100 pt-3">
      <summary
        aria-label={insightEvidenceDisclosureLabel(visibleLocations.length)}
        className="inline-flex cursor-pointer list-none items-center gap-1.5 rounded-md text-xs font-semibold text-slate-400 transition hover:text-slate-600 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-400 focus-visible:ring-offset-2"
      >
        <span>원본 근거</span>
        <span aria-hidden="true">· {visibleLocations.length}개 위치</span>
        <ChevronDown
          aria-hidden="true"
          className="transition-transform group-open:rotate-180"
          size={13}
        />
      </summary>
      <ul className="mt-3 space-y-1.5">
        {visibleLocations.map((location, index) => (
          <li
            className="flex flex-wrap items-center gap-1.5 text-xs leading-5"
            key={`${location.raw}-${index}`}
          >
            {location.sheetName && location.cellRange ? (
              <>
                <span className="max-w-full break-all rounded-md bg-slate-50 px-2 py-1 font-medium text-slate-500">
                  {location.sheetName}
                </span>
                <code className="rounded-md bg-slate-50 px-2 py-1 font-semibold text-slate-500">
                  {location.cellRange}
                </code>
              </>
            ) : (
              <span className="max-w-full break-words rounded-md bg-slate-50 px-2 py-1 text-slate-500">
                {location.raw}
              </span>
            )}
          </li>
        ))}
      </ul>
    </details>
  )
}

export default InsightEvidenceList
