import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'

import {
  createTelegramInvitation,
  listTelegramInvitations,
  listTelegramRecipients,
  removeTelegramRecipient,
  revokeTelegramInvitation,
} from '@/api/telegram'
import { useAuth } from '@/app/providers/auth-context'

export const telegramRecipientsQueryKey = (ownerId: string) =>
  ['telegram', 'recipients', ownerId] as const
export const telegramInvitationsQueryKey = (ownerId: string) =>
  ['telegram', 'invitations', ownerId] as const

const useTelegramRecipientManagement = () => {
  const queryClient = useQueryClient()
  const { user } = useAuth()
  const ownerId = user?.id ?? 'anonymous'
  const recipientsKey = telegramRecipientsQueryKey(ownerId)
  const invitationsKey = telegramInvitationsQueryKey(ownerId)

  const recipients = useQuery({
    queryKey: recipientsKey,
    queryFn: listTelegramRecipients,
  })
  const invitations = useQuery({
    queryKey: invitationsKey,
    queryFn: listTelegramInvitations,
  })

  const createInvitation = useMutation({
    mutationFn: createTelegramInvitation,
    onSuccess: () => {
      void queryClient.invalidateQueries({
        queryKey: invitationsKey,
      })
    },
  })
  const revokeInvitation = useMutation({
    mutationFn: revokeTelegramInvitation,
    onSuccess: () => {
      void queryClient.invalidateQueries({
        queryKey: invitationsKey,
      })
    },
  })
  const removeRecipient = useMutation({
    mutationFn: removeTelegramRecipient,
    onSuccess: () => {
      void queryClient.invalidateQueries({
        queryKey: recipientsKey,
      })
    },
  })

  const refresh = async () => {
    await Promise.all([recipients.refetch(), invitations.refetch()])
  }

  return {
    createInvitation,
    invitations,
    recipients,
    refresh,
    removeRecipient,
    revokeInvitation,
  }
}

export default useTelegramRecipientManagement
