import type { TelegramShareReceipt } from '@/api/analysis/shareTypes'
import apiClient from '@/utils/apiClient'

export const shareAnalysisToTelegram = async (analysisId: string) => {
  const { data } = await apiClient.post<TelegramShareReceipt>(
    `/api/v1/analyses/${analysisId}/shares/telegram`,
  )
  return data
}
