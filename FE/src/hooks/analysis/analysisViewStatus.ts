import type { AnalysisStatus } from '@/api/analysis'

export type AnalysisViewStatus = 'idle' | 'pending' | 'success' | 'error'

const STATUS_TEXT: Record<AnalysisViewStatus, string> = {
  idle: '파일 업로드 대기',
  pending: '분석 진행 중',
  success: '분석 완료',
  error: '분석 실패',
}

interface RunState {
  completed: unknown
  isError: boolean
  isPending: boolean
}

export const viewStatusOf = (run: RunState): AnalysisViewStatus => {
  if (run.isPending) return 'pending'
  if (run.completed) return 'success'
  return run.isError ? 'error' : 'idle'
}

export const viewStatusText = (
  status: AnalysisViewStatus,
  processingStatus: AnalysisStatus | null,
) =>
  status === 'pending' && processingStatus === 'QUEUED'
    ? '분석 대기 중'
    : STATUS_TEXT[status]
