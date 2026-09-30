import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'

import {
  createEmailRecipient,
  listEmailRecipients,
  removeEmailRecipient,
} from '@/api/email'
import { useAuth } from '@/app/providers/auth-context'

export const emailRecipientsQueryKey = (ownerId: string) =>
  ['email', 'recipients', ownerId] as const

const useEmailRecipientManagement = () => {
  const queryClient = useQueryClient()
  const { user } = useAuth()
  const recipientsKey = emailRecipientsQueryKey(user?.id ?? 'anonymous')

  const recipients = useQuery({
    queryKey: recipientsKey,
    queryFn: listEmailRecipients,
  })
  const createRecipient = useMutation({
    mutationFn: createEmailRecipient,
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: recipientsKey })
    },
  })
  const removeRecipient = useMutation({
    mutationFn: removeEmailRecipient,
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: recipientsKey })
    },
  })

  const refresh = async () => {
    await recipients.refetch()
  }

  return {
    createRecipient,
    recipients,
    refresh,
    removeRecipient,
  }
}

export default useEmailRecipientManagement
