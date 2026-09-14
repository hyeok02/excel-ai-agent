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
      <div className="mt-3 space-y-3 rounded-xl border border-slate-100 bg-slate-50/70 p-3">
        <p className="text-[11px] text-slate-500">원본 Excel에서 확인할 시트와 셀 위치</p>
        {groups.map((group) => (
          <div key={group.sheetName === null ? 'unknown' : `sheet:${group.sheetName}`}>
            <div className="mb-2 flex flex-wrap items-center gap-1.5 text-xs">
              <span className="break-all font-semibold text-slate-700">
                {group.sheetName ?? '기타 위치'}
              </span>
              <span className="text-slate-400">{group.locations.length}개</span>
            </div>
            <ul className="flex flex-wrap gap-1.5">
              {group.locations.map((location) => (
                <li key={location.raw}>
                  {location.cellRange ? (
                    <code className="inline-block max-w-full break-all rounded-md border border-slate-200 bg-white px-2 py-1 text-xs font-semibold text-slate-600">
                      {location.cellRange}
                    </code>
                  ) : (
                    <span className="inline-block max-w-full break-words rounded-md border border-slate-200 bg-white px-2 py-1 text-xs text-slate-600">
                      {location.raw}
                    </span>
                  )}
                </li>
              ))}
            </ul>
          </div>
        ))}
      </div>
    </details>
  )
}

export default InsightEvidenceList
