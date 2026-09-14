import { ChevronDown, FileSpreadsheet } from 'lucide-react'

import {
  groupInsightEvidence,
  insightEvidenceDisclosureLabel,
  prepareInsightEvidence,
} from '@/components/analysis/result/insightEvidencePresentation'

const InsightEvidenceList = ({ evidence }: { evidence: string[] }) => {
  const { visibleLocations } = prepareInsightEvidence(evidence, true)
  const groups = groupInsightEvidence(visibleLocations)
  const locationNumbers = new Map(
    visibleLocations.map((location, index) => [location.raw, index + 1]),
  )

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
      <div className="mt-3 divide-y divide-slate-100 rounded-lg border border-slate-200 bg-white">
        {groups.map((group) => (
          <section
            className="px-3 py-2.5"
            key={group.sheetName === null ? 'unknown' : `sheet:${group.sheetName}`}
          >
            <p className="mb-2 break-all text-xs font-semibold text-slate-700">
              {group.sheetName ?? '기타 위치'}
            </p>
            <ol className="grid grid-cols-2 gap-x-3 gap-y-1.5 sm:grid-cols-3">
              {group.locations.map((location) => (
                <li className="flex min-w-0 items-baseline gap-1.5" key={location.raw}>
                  <span className="shrink-0 text-[11px] tabular-nums text-slate-400">
                    {String(locationNumbers.get(location.raw)).padStart(2, '0')}
                  </span>
                  <code className="min-w-0 break-all text-xs font-medium text-slate-700">
                    {location.cellRange ?? location.raw}
                  </code>
                </li>
              ))}
            </ol>
          </section>
        ))}
      </div>
    </details>
  )
}

export default InsightEvidenceList
