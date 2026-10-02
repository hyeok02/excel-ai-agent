import { useEffect, useState } from 'react'

import type { AnalysisDepth, AnalysisMode } from '@/api/analysis'
import {
  type AnalysisViewStatus,
  viewStatusOf,
  viewStatusText,
} from '@/hooks/analysis/analysisViewStatus'
import { useAnalysisProgress } from '@/hooks/analysis/useAnalysisProgress'
import { useAnalysisRun } from '@/hooks/analysis/useAnalysisRun'
import { validateAnalysisFile } from '@/utils/analysis/analysisFile'

export type AnalysisFeedback = 'success' | 'error'
export type { AnalysisViewStatus }

export const useWorkbookAnalysis = () => {
  const [mode, setMode] = useState<AnalysisMode>('BFS')
  const [viewMode, setViewMode] = useState<AnalysisMode | null>(null)
  const [depth, setDepth] = useState<AnalysisDepth>('AUTO')
  const [includeHiddenSheets, setIncludeHiddenSheets] = useState(false)
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

  const status = viewStatusOf(run)

  const executedMode = run.completed?.submission.mode ?? null
  // 복원된 분석은 결과만 남고 File 객체가 없다. 업로드 칸이 비어 보이지
  // 않도록 저장된 파일 정보를 대신 내려보낸다.
  const submission = run.completed?.submission ?? null
  const restoredFile =
    !selectedFile && submission
      ? { name: submission.originalFilename, sizeBytes: submission.sizeBytes }
      : null
  const canShowInsights = run.completed?.result.insightReport != null
  // 결과가 있으면 선택한 방식이 '보기 방식'이 된다.
  const displayMode = executedMode ? (viewMode ?? executedMode) : mode

  const resetView = (hasSelectedFile: boolean) => {
    setClientError(null)
    setFeedback(null)
    setViewMode(null)
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
    run.start(selectedFile, mode, depth, includeHiddenSheets)
  }

  const changeMode = (nextMode: AnalysisMode) => {
    if (nextMode === displayMode) return
    // 저장된 결과로 그릴 수 있으면 재분석 없이 보기만 바꾼다.
    if (executedMode && (nextMode === 'BFS' || canShowInsights)) {
      setViewMode(nextMode)
      return
    }
    // 그릴 데이터가 없으면 그 방식으로 다시 분석할 수 있게 준비한다. 파일은 유지된다.
    setMode(nextMode)
    resetView(Boolean(selectedFile))
  }

  const changeDepth = (nextDepth: AnalysisDepth) => {
    if (nextDepth === depth) return
    setDepth(nextDepth)
    resetView(Boolean(selectedFile))
  }

  // 읽어 들이는 시트가 달라지므로, 켜고 끄면 결과를 비우고 다시 분석하게 한다.
  const changeHiddenSheets = (next: boolean) => {
    if (next === includeHiddenSheets) return
    setIncludeHiddenSheets(next)
    resetView(Boolean(selectedFile))
  }

  return {
    activeAnalysisId: run.analysisId,
    activeStep: progress.activeStep,
    analysisResult: run.completed?.result ?? null,
    analysisResultMode: executedMode,
    changeDepth,
    changeHiddenSheets,
    changeMode,
    clearFile: () => {
      setSelectedFile(null)
      resetView(false)
    },
    depth,
    errorMessage: clientError ?? run.errorMessage,
    feedback,
    includeHiddenSheets,
    insightsNeedReanalysis: Boolean(executedMode) && !canShowInsights,
    isPending: run.isPending,
    mode: displayMode,
    openAnalysis: (nextAnalysisId: string) => {
      setSelectedFile(null)
      setClientError(null)
      setFeedback(null)
      setViewMode(null)
      run.open(nextAnalysisId)
    },
    processingStatus: progress.processingStatus,
    restoredFile,
    selectFile,
    selectedFile,
    startAnalysis,
    status,
    statusText: viewStatusText(status, progress.processingStatus),
  }
}
