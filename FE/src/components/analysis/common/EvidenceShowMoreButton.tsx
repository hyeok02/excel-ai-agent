import { ChevronDown, ChevronUp } from 'lucide-react'

import { evidenceToggleLabel } from '@/components/analysis/common/evidencePreview'

interface EvidenceShowMoreButtonProps {
  expanded: boolean
  hiddenCount: number
  onToggle: () => void
}

const EvidenceShowMoreButton = ({
  expanded,
  hiddenCount,
  onToggle,
}: EvidenceShowMoreButtonProps) => {
  if (hiddenCount <= 0) return null

  return (
    <button
      className="mt-2 inline-flex items-center gap-1 rounded-lg border border-slate-200 bg-white px-3 py-1.5 text-xs font-bold text-slate-600 transition hover:border-brand-200 hover:text-brand-700"
      onClick={onToggle}
      type="button"
    >
      {expanded ? (
        <ChevronUp aria-hidden="true" size={13} />
      ) : (
        <ChevronDown aria-hidden="true" size={13} />
      )}
      {evidenceToggleLabel(expanded, hiddenCount)}
    </button>
  )
}

export default EvidenceShowMoreButton
