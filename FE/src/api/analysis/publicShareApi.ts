import type { AnalysisPublicShareResult } from '@/api/analysis/publicShareTypes'
import apiClient from '@/utils/apiClient'

export const getAnalysisPublicShare = async (token: string) => {
  const { data } = await apiClient.get<AnalysisPublicShareResult>(
    `/api/v1/public/analysis-shares/${encodeURIComponent(token)}`,
  )
  return data
}
