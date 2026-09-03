import { normalizeInsightReport } from '@/api/analysis/insightTypes'
import type {
  AnalysisDepth,
  AnalysisDetails,
  AnalysisHistoryPage,
  AnalysisHistoryQuery,
  AnalysisMode,
  AnalysisResultDetails,
  AnalysisStatus,
  AnalysisSubmission,
  CompletedAnalysis,
} from '@/api/analysis/jobTypes'
import apiClient from '@/utils/apiClient'

export const submitAnalysis = async (
  file: File,
  mode: AnalysisMode,
  depth: AnalysisDepth,
) => {
  const formData = new FormData()
  formData.append('file', file)
  formData.append('mode', mode)
  formData.append('depth', depth)

  const { data } = await apiClient.post<AnalysisSubmission>('/api/v1/analyses', formData)
  return data
}

export const getAnalysisResult = async (analysisId: string) => {
  const { data } = await apiClient.get<AnalysisResultDetails>(
    `/api/v1/analyses/${analysisId}/result`,
  )
  return {
    ...data,
    insightReport: normalizeInsightReport(data.insightReport),
  }
}

export const getAnalysisDetails = async (analysisId: string) => {
  const { data } = await apiClient.get<AnalysisDetails>(`/api/v1/analyses/${analysisId}`)
  return data
}

export const getAnalysisHistory = async (query: AnalysisHistoryQuery = {}) => {
  const { data } = await apiClient.get<AnalysisHistoryPage>('/api/v1/analyses', {
    params: query,
  })
  return data
}

const waitForAnalysis = async (
  analysisId: string,
  onStatusChange?: (status: AnalysisStatus) => void,
) => {
  const startedAt = Date.now()
  const timeoutMs = Number(import.meta.env.VITE_ANALYSIS_TIMEOUT ?? 180_000)
  const pollIntervalMs = Number(import.meta.env.VITE_ANALYSIS_POLL_INTERVAL ?? 1_000)

  while (Date.now() - startedAt < timeoutMs) {
    const details = await getAnalysisDetails(analysisId)
    onStatusChange?.(details.status)
    if (details.status === 'COMPLETED') return
    if (details.status === 'FAILED') {
      throw new Error('Excel 분석 처리에 실패했습니다.')
    }
    await new Promise((resolve) => window.setTimeout(resolve, pollIntervalMs))
  }

  throw new Error(
    '분석 대기 시간이 초과되었습니다. 분석 이력에서 처리 상태를 확인해주세요.',
  )
}

export const analyzeWorkbook = async (
  file: File,
  mode: AnalysisMode,
  depth: AnalysisDepth,
  onStatusChange?: (status: AnalysisStatus) => void,
  onSubmitted?: (submission: AnalysisSubmission) => void,
): Promise<CompletedAnalysis> => {
  const submission = await submitAnalysis(file, mode, depth)
  onSubmitted?.(submission)
  onStatusChange?.(submission.status)
  await waitForAnalysis(submission.analysisId, onStatusChange)
  const result = await getAnalysisResult(submission.analysisId)

  return { submission, result }
}

/** 이미 접수된 분석을 이어받는다. 진행 중이면 완료될 때까지 기다린다. */
export const resumeAnalysis = async (
  analysisId: string,
  onStatusChange?: (status: AnalysisStatus) => void,
): Promise<CompletedAnalysis> => {
  const submission = await getAnalysisDetails(analysisId)
  onStatusChange?.(submission.status)
  if (submission.status === 'FAILED') {
    throw new Error('이 분석은 처리에 실패하여 결과를 열 수 없습니다.')
  }
  if (submission.status !== 'COMPLETED') {
    await waitForAnalysis(analysisId, onStatusChange)
  }
  const result = await getAnalysisResult(analysisId)

  return { submission, result }
}
