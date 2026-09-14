import EvidenceDisclosure from '@/components/analysis/common/EvidenceDisclosure'
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
    <EvidenceDisclosure
      ariaLabel={insightEvidenceDisclosureLabel(visibleLocations.length)}
      count={visibleLocations.length}
    >
      <div className="space-y-3">
        {groups.map((group) => (
          <section
            key={group.sheetName === null ? 'unknown' : `sheet:${group.sheetName}`}
          >
            <p className="mb-1 break-all text-xs font-medium text-slate-500">
              {group.sheetName ?? '기타 위치'}
            </p>
            <ul className="space-y-1.5">
              {group.locations.map((location) => (
                <li
                  className="rounded-lg border border-slate-200 bg-slate-50/60 px-3 py-2"
                  key={location.raw}
                >
                  <code className="break-all text-xs font-medium text-slate-700">
                    {location.cellRange ?? location.raw}
                  </code>
                </li>
              ))}
            </ul>
          </section>
        ))}
      </div>
    </EvidenceDisclosure>
  )
}

export default InsightEvidenceList
