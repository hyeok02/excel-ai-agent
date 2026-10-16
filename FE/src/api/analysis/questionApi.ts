import type {
  WorkbookQuestionAnswer,
  WorkbookQuestionContext,
  WorkbookQuestionHistoryPage,
} from '@/api/analysis/questionTypes'
import apiClient from '@/utils/apiClient'

export const getWorkbookQuestionHistory = async (
  analysisId: string,
  before: string | null = null,
  signal?: AbortSignal,
): Promise<WorkbookQuestionHistoryPage> => {
  const { data } = await apiClient.get<WorkbookQuestionHistoryPage>(
    `/api/v1/analyses/${analysisId}/questions`,
    { params: { size: 30, ...(before ? { before } : {}) }, signal },
  )
  return data
}

export const askWorkbookQuestion = async (
  analysisId: string,
  question: string,
  context?: WorkbookQuestionContext,
): Promise<WorkbookQuestionAnswer> => {
  const { data } = await apiClient.post<WorkbookQuestionAnswer>(
    `/api/v1/analyses/${analysisId}/questions`,
    { question, ...(context ? { context } : {}) },
  )
  return data
}
