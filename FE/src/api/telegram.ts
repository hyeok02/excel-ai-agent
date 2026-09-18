import apiClient from '@/utils/apiClient'

export const TELEGRAM_SHARE_RECIPIENT_LIMIT = 50

export type TelegramRecipientStatus = 'ACTIVE' | 'DISCONNECTED'
export type TelegramInvitationStatus = 'ACTIVE' | 'CONSUMED' | 'EXPIRED' | 'REVOKED'

export interface TelegramRecipient {
  id: string
  displayName: string
  username: string | null
  connectedAt: string
  status: TelegramRecipientStatus
}

export interface TelegramInvitation {
  id: string
  label: string | null
  createdAt: string
  expiresAt: string
  status: TelegramInvitationStatus
}

export interface CreatedTelegramInvitation extends TelegramInvitation {
  inviteUrl: string
}

export interface TelegramDeliveryResult {
  recipientId: string | null
  recipientName: string
  success: boolean
  errorMessage: string | null
}

export interface TelegramShareReceipt {
  sentAt: string
  requestedCount: number
  successCount: number
  failureCount: number
  deliveries: TelegramDeliveryResult[]
}

export const listTelegramRecipients = async () => {
  const { data } = await apiClient.get<TelegramRecipient[]>('/api/v1/telegram/recipients')
  return data
}

export const listTelegramInvitations = async () => {
  const { data } = await apiClient.get<TelegramInvitation[]>(
    '/api/v1/telegram/invitations',
  )
  return data
}

export const createTelegramInvitation = async (label?: string) => {
  const { data } = await apiClient.post<CreatedTelegramInvitation>(
    '/api/v1/telegram/invitations',
    label ? { label } : {},
  )
  return data
}

export const revokeTelegramInvitation = async (invitationId: string) => {
  await apiClient.delete(`/api/v1/telegram/invitations/${invitationId}`)
}

export const removeTelegramRecipient = async (recipientId: string) => {
  await apiClient.delete(`/api/v1/telegram/recipients/${recipientId}`)
}
