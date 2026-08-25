import { useMutation } from '@tanstack/react-query'
import { useEffect, useState } from 'react'

import {
  type AnalysisDepth,
  type AnalysisMode,
  type AnalysisStatus,
  analyzeWorkbook,
} from '@/api/analysis'
import { validateAnalysisFile } from '@/utils/analysis/analysisFile'
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
  const [depth, setDepth] = useState<AnalysisDepth>('AUTO')
  const [selectedFile, setSelectedFile] = useState<File | null>(null)
  const [clientError, setClientError] = useState<string | null>(null)
  const [feedback, setFeedback] = useState<AnalysisFeedback | null>(null)
  const [processingStatus, setProcessingStatus] = useState<AnalysisStatus | null>(null)

  const analysisMutation = useMutation({
    mutationFn: ({
      file,
      analysisMode,
      analysisDepth,
    }: {
      file: File
      analysisMode: AnalysisMode
      analysisDepth: AnalysisDepth
    }) => analyzeWorkbook(file, analysisMode, analysisDepth, setProcessingStatus),
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
    setProcessingStatus(null)
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
    setProcessingStatus(null)
    analysisMutation.mutate({
      file: selectedFile,
      analysisMode: mode,
      analysisDepth: depth,
    })
  }

  const clearFile = () => {
    setSelectedFile(null)
    setClientError(null)
    setFeedback(null)
    setProcessingStatus(null)
    analysisMutation.reset()
  }

  const changeMode = (nextMode: AnalysisMode) => {
    if (nextMode === mode) {
      return
    }

    setMode(nextMode)
    setClientError(null)
    setFeedback(null)
    analysisMutation.reset()
    setProcessingStatus(null)
  }

  const changeDepth = (nextDepth: AnalysisDepth) => {
    if (nextDepth === depth) {
      return
    }

    setDepth(nextDepth)
    setClientError(null)
    setFeedback(null)
    analysisMutation.reset()
    setProcessingStatus(null)
  }

  return {
    analysisResult: analysisMutation.data?.result ?? null,
    analysisResultMode: analysisMutation.data?.submission.mode ?? null,
    changeDepth,
    changeMode,
    clearFile,
    depth,
    errorMessage:
      clientError ??
      (analysisMutation.isError ? getErrorMessage(analysisMutation.error) : null),
    feedback,
    isPending: analysisMutation.isPending,
    mode,
    selectFile,
    selectedFile,
    startAnalysis,
    status,
    statusText:
      status === 'pending' && processingStatus === 'QUEUED'
        ? '분석 대기 중'
        : STATUS_TEXT[status],
  }
}
