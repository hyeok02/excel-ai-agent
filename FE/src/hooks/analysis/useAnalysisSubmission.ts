import { useMutation, useQueryClient } from '@tanstack/react-query'
import { useLayoutEffect, useState } from 'react'

import { type AnalysisDepth, type AnalysisMode, analyzeWorkbook } from '@/api/analysis'
import {
  type AnalysisRequestScope,
  createAnalysisRequestScopes,
} from '@/hooks/analysis/analysisRequestScope'
import type { useAnalysisProgress } from '@/hooks/analysis/useAnalysisProgress'

interface SubmissionInput {
  file: File
  analysisMode: AnalysisMode
  analysisDepth: AnalysisDepth
  includeHiddenSheets: boolean
}

export const useAnalysisSubmission = (
  analysisId: string | null,
  progress: ReturnType<typeof useAnalysisProgress>,
  handlers: {
    onError: () => void
    onSuccess: () => void
    onSubmitted: (id: string) => void
  },
) => {
  const queryClient = useQueryClient()
  const [requests] = useState(createAnalysisRequestScopes)
  const mutation = useMutation({
    mutationFn: ({
      scope,
      ...input
    }: SubmissionInput & { scope: AnalysisRequestScope }) =>
      analyzeWorkbook(
        input.file,
        input.analysisMode,
        input.analysisDepth,
        input.includeHiddenSheets,
        (status) => {
          if (scope.isActive()) progress.updateStatus(status)
        },
        (submission) => {
          if (!scope.isActive()) return
          scope.analysisId = submission.analysisId
          handlers.onSubmitted(submission.analysisId)
        },
        scope.signal,
      ),
    onError: (_, { scope }) => {
      if (scope.isActive()) handlers.onError()
    },
    onSuccess: (_, { scope }) => {
      if (!scope.isActive()) return
      handlers.onSuccess()
      void queryClient.invalidateQueries({ queryKey: ['analysis-history'] })
    },
  })
  const resetMutation = mutation.reset
  const resetProgress = progress.reset

  useLayoutEffect(() => () => requests.cancel(), [requests])
  // Browser back/forward also changes the view, without calling open() or reset().
  useLayoutEffect(() => {
    if (!requests.differsFrom(analysisId)) return
    requests.cancel()
    resetMutation()
    resetProgress(false)
  }, [analysisId, requests, resetMutation, resetProgress])

  return {
    ...mutation,
    reset: () => {
      requests.cancel()
      resetMutation()
    },
    start: (input: SubmissionInput) => {
      const scope = requests.begin(analysisId)
      mutation.mutate({ ...input, scope })
    },
  }
}
