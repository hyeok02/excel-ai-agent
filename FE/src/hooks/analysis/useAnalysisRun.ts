import { useQuery, useQueryClient } from '@tanstack/react-query'
import { useState } from 'react'
import { useSearchParams } from 'react-router-dom'

import { type AnalysisDepth, type AnalysisMode, resumeAnalysis } from '@/api/analysis'
import type { useAnalysisProgress } from '@/hooks/analysis/useAnalysisProgress'
import { useAnalysisSubmission } from '@/hooks/analysis/useAnalysisSubmission'
import { getErrorMessage } from '@/utils/apiClient'

export const ANALYSIS_ID_PARAM = 'id'
export const ANALYSIS_HISTORY_QUERY_KEY = ['analysis-history']

type AnalysisProgress = ReturnType<typeof useAnalysisProgress>

interface AnalysisRunHandlers {
  onError: () => void
  onSuccess: () => void
}

/**
 * 분석 실행과 복원을 함께 관리한다.
 *
 * 접수된 분석 ID를 주소에 남겨 두므로, 진행 중에 새로고침해도 같은 분석을
 * 이어받고 이력에서 고른 분석도 같은 경로로 열린다.
 */
export const useAnalysisRun = (
  progress: AnalysisProgress,
  handlers: AnalysisRunHandlers,
) => {
  const [searchParams, setSearchParams] = useSearchParams()
  const queryClient = useQueryClient()
  // 닫은 분석은 주소에서 지워지기 전에도 다시 불러오지 않는다.
  const [dismissedId, setDismissedId] = useState<string | null>(null)
  const analysisId = searchParams.get(ANALYSIS_ID_PARAM)

  const mutation = useAnalysisSubmission(analysisId, progress, {
    ...handlers,
    onSubmitted: (id) => setSearchParams({ [ANALYSIS_ID_PARAM]: id }, { replace: true }),
  })

  const restored = useQuery({
    enabled:
      Boolean(analysisId) &&
      analysisId !== dismissedId &&
      !mutation.isPending &&
      !mutation.data,
    queryFn: ({ signal }) =>
      resumeAnalysis(analysisId as string, progress.updateStatus, signal),
    queryKey: ['analysis', analysisId],
    retry: false,
    staleTime: Number.POSITIVE_INFINITY,
  })

  const cancelObservation = () => {
    mutation.reset()
    void queryClient.cancelQueries({ queryKey: ['analysis', analysisId], exact: true })
  }

  const forgetOpenAnalysis = () => {
    if (!analysisId) return
    const next = new URLSearchParams(searchParams)
    next.delete(ANALYSIS_ID_PARAM)
    setSearchParams(next, { replace: true })
  }

  return {
    analysisId,
    completed: mutation.data ?? restored.data ?? null,
    errorMessage: mutation.isError
      ? getErrorMessage(mutation.error)
      : restored.isError
        ? getErrorMessage(restored.error)
        : null,
    isError: mutation.isError || restored.isError,
    isPending: mutation.isPending || restored.isFetching,
    open: (nextAnalysisId: string) => {
      if (
        nextAnalysisId === analysisId &&
        analysisId !== dismissedId &&
        !mutation.isError &&
        !restored.isError
      )
        return
      setDismissedId(null)
      cancelObservation()
      progress.reset(false)
      setSearchParams({ [ANALYSIS_ID_PARAM]: nextAnalysisId })
      if (nextAnalysisId === analysisId) void restored.refetch()
    },
    reset: () => {
      setDismissedId(analysisId)
      cancelObservation()
      forgetOpenAnalysis()
    },
    start: (
      file: File,
      analysisMode: AnalysisMode,
      analysisDepth: AnalysisDepth,
      includeHiddenSheets: boolean,
    ) => {
      cancelObservation()
      mutation.start({ analysisDepth, analysisMode, file, includeHiddenSheets })
    },
  }
}
