import type { AnalysisDetails } from '@/api/analysis'
import {
  formatAnalyzedAt,
  formatFileSize,
  STATUS_LABEL,
  STATUS_TONE,
} from '@/components/analysis/upload/analysisHistoryPresentation'
import { cn } from '@/utils/cn'

interface AnalysisHistoryItemProps {
  isActive: boolean
  item: AnalysisDetails
  onOpen: (analysisId: string) => void
}

const AnalysisHistoryItem = ({ isActive, item, onOpen }: AnalysisHistoryItemProps) => {
  const failed = item.status === 'FAILED'

  return (
    <button
      className={cn(
        'w-full rounded-xl border px-3 py-2.5 text-left transition',
        failed
          ? 'cursor-not-allowed border-slate-200 bg-slate-50 opacity-70'
          : isActive
            ? 'border-brand-300 bg-brand-50/70'
            : 'border-slate-200 hover:border-brand-200 hover:bg-brand-50/30',
      )}
      disabled={failed}
      onClick={() => onOpen(item.analysisId)}
      type="button"
    >
      <span className="block truncate text-sm font-bold text-slate-700">
        {item.originalFilename}
      </span>
      <span className="mt-1 flex items-center justify-between gap-2 text-[11px] text-slate-400">
        <span>
          {formatAnalyzedAt(item.createdAt)} · {item.mode} ·{' '}
          {formatFileSize(item.sizeBytes)}
        </span>
        <span className="flex shrink-0 items-center gap-2">
          {!item.sourceAvailable && item.status === 'COMPLETED' && (
            <span className="font-extrabold text-amber-600">원본 보관 만료</span>
          )}
          <span className={cn('font-extrabold', STATUS_TONE[item.status])}>
            {failed ? '분석 실패 · 열 수 없음' : STATUS_LABEL[item.status]}
          </span>
        </span>
      </span>
    </button>
  )
}

export default AnalysisHistoryItem
