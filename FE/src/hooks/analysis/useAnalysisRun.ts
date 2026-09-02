import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useSearchParams } from 'react-router-dom'

import {
  type AnalysisDepth,
  type AnalysisMode,
  analyzeWorkbook,
  resumeAnalysis,
} from '@/api/analysis'
import type { useAnalysisProgress } from '@/hooks/analysis/useAnalysisProgress'
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
  const analysisId = searchParams.get(ANALYSIS_ID_PARAM)

  const mutation = useMutation({
    mutationFn: ({
      file,
      analysisMode,
      analysisDepth,
    }: {
      file: File
      analysisMode: AnalysisMode
      analysisDepth: AnalysisDepth
    }) =>
      analyzeWorkbook(
        file,
        analysisMode,
        analysisDepth,
        progress.updateStatus,
        (submission) =>
          setSearchParams(
            { [ANALYSIS_ID_PARAM]: submission.analysisId },
            { replace: true },
          ),
      ),
    onError: handlers.onError,
    onSuccess: () => {
      handlers.onSuccess()
      void queryClient.invalidateQueries({ queryKey: ANALYSIS_HISTORY_QUERY_KEY })
    },
  })

  const restored = useQuery({
    enabled: Boolean(analysisId) && !mutation.isPending && !mutation.data,
    queryFn: () => resumeAnalysis(analysisId as string, progress.updateStatus),
    queryKey: ['analysis', analysisId],
    retry: false,
    staleTime: Number.POSITIVE_INFINITY,
  })

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
      mutation.reset()
      progress.reset(false)
      setSearchParams({ [ANALYSIS_ID_PARAM]: nextAnalysisId })
    },
    reset: () => {
      mutation.reset()
      forgetOpenAnalysis()
    },
    start: (file: File, analysisMode: AnalysisMode, analysisDepth: AnalysisDepth) =>
      mutation.mutate({ file, analysisMode, analysisDepth }),
  }
}
