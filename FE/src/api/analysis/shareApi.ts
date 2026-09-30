import type { TelegramShareReceipt } from '@/api/analysis/shareTypes'
import type { EmailShareReceipt } from '@/api/email'
import apiClient from '@/utils/apiClient'

export const shareAnalysisToTelegram = async (
  analysisId: string,
  recipientIds: string[],
) => {
  const { data } = await apiClient.post<TelegramShareReceipt>(
    `/api/v1/analyses/${analysisId}/shares/telegram`,
    { recipientIds },
  )
  return data
}

export const shareAnalysisToEmail = async (
  analysisId: string,
  recipientIds: string[],
) => {
  const { data } = await apiClient.post<EmailShareReceipt>(
    `/api/v1/analyses/${analysisId}/shares/email`,
    { recipientIds },
  )
  return data
}
