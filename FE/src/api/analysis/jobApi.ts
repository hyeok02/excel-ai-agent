import { normalizeInsightReport } from '@/api/analysis/insightTypes'
import { createAnalysisJobRunner } from '@/api/analysis/jobRunner'
import type {
  AnalysisDepth,
  AnalysisDetails,
  AnalysisHistoryPage,
  AnalysisHistoryQuery,
  AnalysisMode,
  AnalysisResultDetails,
  AnalysisSubmission,
} from '@/api/analysis/jobTypes'
import apiClient from '@/utils/apiClient'

export const submitAnalysis = async (
  file: File,
  mode: AnalysisMode,
  depth: AnalysisDepth,
  includeHiddenSheets: boolean,
  signal?: AbortSignal,
) => {
  const formData = new FormData()
  formData.append('file', file)
  formData.append('mode', mode)
  formData.append('depth', depth)
  formData.append('includeHiddenSheets', String(includeHiddenSheets))

  const { data } = await apiClient.post<AnalysisSubmission>(
    '/api/v1/analyses',
    formData,
    {
      signal,
    },
  )
  return data
}

export const getAnalysisResult = async (analysisId: string, signal?: AbortSignal) => {
  const { data } = await apiClient.get<AnalysisResultDetails>(
    `/api/v1/analyses/${analysisId}/result`,
    { signal },
  )
  return {
    ...data,
    insightReport: normalizeInsightReport(data.insightReport),
  }
}

export const getAnalysisDetails = async (analysisId: string, signal?: AbortSignal) => {
  const { data } = await apiClient.get<AnalysisDetails>(
    `/api/v1/analyses/${analysisId}`,
    {
      signal,
    },
  )
  return data
}

export const getAnalysisHistory = async (query: AnalysisHistoryQuery = {}) => {
  const { data } = await apiClient.get<AnalysisHistoryPage>('/api/v1/analyses', {
    params: query,
  })
  return data
}

const runner = createAnalysisJobRunner({
  submit: submitAnalysis,
  details: getAnalysisDetails,
  result: getAnalysisResult,
  timeoutMs: Number(import.meta.env.VITE_ANALYSIS_TIMEOUT ?? 180_000),
  pollIntervalMs: Number(import.meta.env.VITE_ANALYSIS_POLL_INTERVAL ?? 1_000),
})

export const analyzeWorkbook = runner.analyze
export const resumeAnalysis = runner.resume
