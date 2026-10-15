import type {
  WorkbookQuestionAnswer,
  WorkbookQuestionContext,
} from '@/api/analysis/questionTypes'
import apiClient from '@/utils/apiClient'

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
