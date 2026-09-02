import type { AnalysisStatus } from '@/api/analysis'

export const HISTORY_PAGE_SIZE = 20

export const STATUS_LABEL: Record<AnalysisStatus, string> = {
  QUEUED: '대기',
  PROCESSING: '진행 중',
  COMPLETED: '완료',
  FAILED: '실패',
}

export const STATUS_TONE: Record<AnalysisStatus, string> = {
  QUEUED: 'text-slate-400',
  PROCESSING: 'text-brand-700',
  COMPLETED: 'text-emerald-600',
  FAILED: 'text-rose-600',
}

export const formatAnalyzedAt = (value: string) =>
  new Date(value).toLocaleString('ko-KR', {
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
    month: '2-digit',
    year: 'numeric',
  })

export const formatFileSize = (bytes: number) => {
  const megabytes = bytes / (1024 * 1024)
  return megabytes >= 1
    ? `${megabytes.toFixed(1)}MB`
    : `${Math.max(1, Math.round(bytes / 1024))}KB`
}
