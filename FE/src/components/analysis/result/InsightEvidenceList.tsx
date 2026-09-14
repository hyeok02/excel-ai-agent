import { ChevronDown, FileSpreadsheet } from 'lucide-react'

import {
  groupInsightEvidence,
  insightEvidenceDisclosureLabel,
  prepareInsightEvidence,
} from '@/components/analysis/result/insightEvidencePresentation'

const InsightEvidenceList = ({ evidence }: { evidence: string[] }) => {
  const { visibleLocations } = prepareInsightEvidence(evidence, true)
  const groups = groupInsightEvidence(visibleLocations)

  if (visibleLocations.length === 0) return null

  return (
    <details className="group mt-4 border-t border-slate-100 pt-3">
      <summary
        aria-label={insightEvidenceDisclosureLabel(visibleLocations.length)}
        className="flex w-full cursor-pointer list-none items-center justify-between gap-2 rounded-md text-xs font-semibold text-slate-500 transition hover:text-slate-700 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-400 focus-visible:ring-offset-2"
      >
        <span className="inline-flex items-center gap-1.5">
          <FileSpreadsheet aria-hidden="true" size={14} />
          원본 근거 <span aria-hidden="true">· {visibleLocations.length}개 위치</span>
        </span>
        <ChevronDown
          aria-hidden="true"
          className="transition-transform group-open:rotate-180"
          size={13}
        />
      </summary>
      <div className="mt-3 space-y-3">
        {groups.map((group) => (
          <section
            key={group.sheetName === null ? 'unknown' : `sheet:${group.sheetName}`}
          >
            <p className="mb-1 break-all text-xs font-medium text-slate-500">
              {group.sheetName ?? '기타 위치'}
            </p>
            <ul className="divide-y divide-slate-100">
              {group.locations.map((location) => (
                <li className="py-1.5 first:pt-0 last:pb-0" key={location.raw}>
                  <code className="break-all text-xs font-medium text-slate-700">
                    {location.cellRange ?? location.raw}
                  </code>
                </li>
              ))}
            </ul>
          </section>
        ))}
      </div>
    </details>
  )
}

export default InsightEvidenceList
