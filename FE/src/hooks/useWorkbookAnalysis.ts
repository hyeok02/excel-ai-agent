import { useMutation } from '@tanstack/react-query'
import { useEffect, useState } from 'react'

import { type AnalysisMode, analyzeWorkbook } from '@/api/analysis'
import { validateAnalysisFile } from '@/utils/analysisFile'
import { getErrorMessage } from '@/utils/apiClient'

export type AnalysisFeedback = 'success' | 'error'
export type AnalysisViewStatus = 'idle' | 'pending' | 'success' | 'error'

const STATUS_TEXT: Record<AnalysisViewStatus, string> = {
  idle: '파일 업로드 대기',
  pending: '분석 진행 중',
  success: '분석 완료',
  error: '분석 실패',
}

export const useWorkbookAnalysis = () => {
  const [mode, setMode] = useState<AnalysisMode>('BFS')
  const [selectedFile, setSelectedFile] = useState<File | null>(null)
  const [clientError, setClientError] = useState<string | null>(null)
  const [feedback, setFeedback] = useState<AnalysisFeedback | null>(null)

  const analysisMutation = useMutation({
    mutationFn: ({ file, analysisMode }: { file: File; analysisMode: AnalysisMode }) =>
      analyzeWorkbook(file, analysisMode),
    onError: () => setFeedback('error'),
    onSuccess: () => setFeedback('success'),
  })

  useEffect(() => {
    if (!feedback) {
      return undefined
    }

    const timeoutId = window.setTimeout(() => setFeedback(null), 1900)
    return () => window.clearTimeout(timeoutId)
  }, [feedback])

  const status: AnalysisViewStatus = analysisMutation.isPending
    ? 'pending'
    : analysisMutation.isSuccess
      ? 'success'
      : analysisMutation.isError
        ? 'error'
        : 'idle'

  const selectFile = (file: File) => {
    const validationMessage = validateAnalysisFile(file)

    analysisMutation.reset()
    setClientError(validationMessage)
    setSelectedFile(validationMessage ? null : file)
    setFeedback(validationMessage ? 'error' : null)
  }

  const startAnalysis = () => {
    if (!selectedFile) {
      setClientError('분석할 Excel 파일을 먼저 선택해주세요.')
      setFeedback('error')
      return
    }

    setClientError(null)
    setFeedback(null)
    analysisMutation.mutate({ file: selectedFile, analysisMode: mode })
  }

  const clearFile = () => {
    setSelectedFile(null)
    setClientError(null)
    setFeedback(null)
    analysisMutation.reset()
  }

  return {
    analysisResult: analysisMutation.data?.result ?? null,
    clearFile,
    errorMessage:
      clientError ??
      (analysisMutation.isError ? getErrorMessage(analysisMutation.error) : null),
    feedback,
    isPending: analysisMutation.isPending,
    mode,
    selectFile,
    selectedFile,
    setMode,
    startAnalysis,
    status,
    statusText: STATUS_TEXT[status],
  }
}
