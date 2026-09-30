import apiClient from '@/utils/apiClient'

export const EMAIL_SHARE_RECIPIENT_LIMIT = 50

export type EmailRecipientStatus = 'ACTIVE'

export interface EmailRecipient {
  id: string
  displayName: string
  email: string
  createdAt: string
  status: EmailRecipientStatus
}

export interface CreateEmailRecipientRequest {
  displayName?: string
  email: string
}

export interface EmailDeliveryResult {
  recipientId: string | null
  recipientName: string
  success: boolean
  errorMessage: string | null
}

export interface EmailShareReceipt {
  sentAt: string
  requestedCount: number
  successCount: number
  failureCount: number
  deliveries: EmailDeliveryResult[]
}

export const listEmailRecipients = async () => {
  const { data } = await apiClient.get<EmailRecipient[]>('/api/v1/email/recipients')
  return data
}

export const createEmailRecipient = async (request: CreateEmailRecipientRequest) => {
  const { data } = await apiClient.post<EmailRecipient>(
    '/api/v1/email/recipients',
    request,
  )
  return data
}

export const removeEmailRecipient = async (recipientId: string) => {
  await apiClient.delete(`/api/v1/email/recipients/${recipientId}`)
}
