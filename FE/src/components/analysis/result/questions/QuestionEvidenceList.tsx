import { useState } from 'react'

import type { WorkbookQuestionEvidence } from '@/api/analysis'
import EvidenceDisclosure from '@/components/analysis/common/EvidenceDisclosure'
import { limitEvidence } from '@/components/analysis/common/evidencePreview'
import EvidenceShowMoreButton from '@/components/analysis/common/EvidenceShowMoreButton'
import ResponsiveCardColumns from '@/components/analysis/common/ResponsiveCardColumns'
import QuestionEvidenceCard from '@/components/analysis/result/questions/QuestionEvidenceCard'
import { questionEvidenceDisclosureLabel } from '@/components/analysis/result/questions/questionPresentation'

const QuestionEvidenceList = ({ evidence }: { evidence: WorkbookQuestionEvidence[] }) => {
  const [expandedFormulaKey, setExpandedFormulaKey] = useState<string | null>(null)
  const [showAll, setShowAll] = useState(false)
  const { visible, hiddenCount } = limitEvidence(evidence, showAll)

  if (evidence.length === 0) return null

  const evidenceKey = (item: WorkbookQuestionEvidence) =>
    `${item.sheetName}-${item.reference}`

  return (
    <EvidenceDisclosure
      ariaLabel={questionEvidenceDisclosureLabel(evidence.length)}
      count={evidence.length}
    >
      <ResponsiveCardColumns
        breakpoint="md"
        density="compact"
        getKey={evidenceKey}
        items={visible}
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
      <EvidenceShowMoreButton
        expanded={showAll}
        hiddenCount={hiddenCount}
        onToggle={() => setShowAll((current) => !current)}
      />
    </EvidenceDisclosure>
  )
}

export default QuestionEvidenceList
