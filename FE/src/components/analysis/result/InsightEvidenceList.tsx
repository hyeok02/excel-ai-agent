import { useState } from 'react'

import EvidenceDisclosure from '@/components/analysis/common/EvidenceDisclosure'
import { limitEvidence } from '@/components/analysis/common/evidencePreview'
import EvidenceShowMoreButton from '@/components/analysis/common/EvidenceShowMoreButton'
import {
  groupInsightEvidence,
  insightEvidenceDisclosureLabel,
  prepareInsightEvidence,
} from '@/components/analysis/result/insightEvidencePresentation'

const InsightEvidenceList = ({ evidence }: { evidence: string[] }) => {
  const [showAll, setShowAll] = useState(false)
  const { visibleLocations } = prepareInsightEvidence(evidence, true)
  const { visible, hiddenCount } = limitEvidence(visibleLocations, showAll)
  const groups = groupInsightEvidence(visible)

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
      <EvidenceShowMoreButton
        expanded={showAll}
        hiddenCount={hiddenCount}
        onToggle={() => setShowAll((current) => !current)}
      />
    </EvidenceDisclosure>
  )
}

export default InsightEvidenceList
