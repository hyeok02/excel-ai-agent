import { useEffect, useState } from 'react'

import type { AnalysisDepth, AnalysisMode } from '@/api/analysis'
import { useAnalysisProgress } from '@/hooks/analysis/useAnalysisProgress'
import { useAnalysisRun } from '@/hooks/analysis/useAnalysisRun'
import { validateAnalysisFile } from '@/utils/analysis/analysisFile'

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
  const progress = useAnalysisProgress()
  const run = useAnalysisRun(progress, {
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

  const status: AnalysisViewStatus = run.isPending
    ? 'pending'
    : run.completed
      ? 'success'
      : run.isError
        ? 'error'
        : 'idle'

  const resetView = (hasSelectedFile: boolean) => {
    setClientError(null)
    setFeedback(null)
    progress.reset(hasSelectedFile)
    run.reset()
  }

  const selectFile = (file: File) => {
    const validationMessage = validateAnalysisFile(file)

    resetView(!validationMessage)
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
    progress.begin()
    run.start(selectedFile, mode, depth)
  }

  const changeMode = (nextMode: AnalysisMode) => {
    if (nextMode === mode) return
    setMode(nextMode)
    resetView(Boolean(selectedFile))
  }

  const changeDepth = (nextDepth: AnalysisDepth) => {
    if (nextDepth === depth) return
    setDepth(nextDepth)
    resetView(Boolean(selectedFile))
  }

  return {
    activeAnalysisId: run.analysisId,
    activeStep: progress.activeStep,
    analysisResult: run.completed?.result ?? null,
    analysisResultMode: run.completed?.submission.mode ?? null,
    changeDepth,
    changeMode,
    clearFile: () => {
      setSelectedFile(null)
      resetView(false)
    },
    depth,
    errorMessage: clientError ?? run.errorMessage,
    feedback,
    isPending: run.isPending,
    mode,
    openAnalysis: (nextAnalysisId: string) => {
      setSelectedFile(null)
      setClientError(null)
      setFeedback(null)
      run.open(nextAnalysisId)
    },
    processingStatus: progress.processingStatus,
    selectFile,
    selectedFile,
    startAnalysis,
    status,
    statusText:
      status === 'pending' && progress.processingStatus === 'QUEUED'
        ? '분석 대기 중'
        : STATUS_TEXT[status],
  }
}
