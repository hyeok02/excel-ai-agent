import { useMutation, useQuery } from '@tanstack/react-query'
import { useMemo, useState } from 'react'

import { shareAnalysisToEmail } from '@/api/analysis'
import { EMAIL_SHARE_RECIPIENT_LIMIT, listEmailRecipients } from '@/api/email'
import { useAuth } from '@/app/providers/auth-context'
import EmailRecipientSelector from '@/components/analysis/result/EmailRecipientSelector'
import EmailShareDialogHeader from '@/components/analysis/result/EmailShareDialogHeader'
import EmailShareFooter from '@/components/analysis/result/EmailShareFooter'
import {
  EmailRecipientsEmpty,
  EmailRecipientsError,
  EmailRecipientsLoading,
} from '@/components/analysis/result/EmailShareRecipientStates'
import { emailRecipientsQueryKey } from '@/hooks/email/useEmailRecipientManagement'
import useDialogFocusTrap from '@/hooks/useDialogFocusTrap'
import { getErrorMessage } from '@/utils/apiClient'

interface EmailShareDialogProps {
  analysisId: string
  onClose: () => void
}

const EmailShareDialog = ({ analysisId, onClose }: EmailShareDialogProps) => {
  const [selectionOverride, setSelectionOverride] = useState<Set<string> | null>(null)
  const { user } = useAuth()
  const recipients = useQuery({
    queryKey: emailRecipientsQueryKey(user?.id ?? 'anonymous'),
    queryFn: listEmailRecipients,
  })
  const activeRecipients = useMemo(
    () => (recipients.data ?? []).filter((recipient) => recipient.status === 'ACTIVE'),
    [recipients.data],
  )
  const defaultSelectedIds = useMemo(
    () =>
      new Set(
        activeRecipients
          .slice(0, EMAIL_SHARE_RECIPIENT_LIMIT)
          .map((recipient) => recipient.id),
      ),
    [activeRecipients],
  )
  const activeRecipientIds = useMemo(
    () => new Set(activeRecipients.map((recipient) => recipient.id)),
    [activeRecipients],
  )
  const selectedIds = useMemo(
    () =>
      selectionOverride === null
        ? defaultSelectedIds
        : new Set(
            [...selectionOverride].filter((recipientId) =>
              activeRecipientIds.has(recipientId),
            ),
          ),
    [activeRecipientIds, defaultSelectedIds, selectionOverride],
  )
  const share = useMutation({
    mutationFn: (recipientIds: string[]) =>
      shareAnalysisToEmail(analysisId, recipientIds),
    onSuccess: (receipt) => {
      if (receipt.failureCount > 0) {
        setSelectionOverride(
          new Set(
            receipt.deliveries.flatMap((delivery) =>
              !delivery.success && delivery.recipientId ? [delivery.recipientId] : [],
            ),
          ),
        )
      }
    },
  })
  const dialogRef = useDialogFocusTrap({ isCloseBlocked: share.isPending, onClose })

  const changeSelection = (next: Set<string>) => {
    setSelectionOverride(next)
    share.reset()
  }

  const toggleRecipient = (recipientId: string) => {
    const next = new Set(selectedIds)
    if (next.has(recipientId)) next.delete(recipientId)
    else if (next.size < EMAIL_SHARE_RECIPIENT_LIMIT) next.add(recipientId)
    changeSelection(next)
  }

  const toggleAll = () => {
    changeSelection(
      selectedIds.size === Math.min(activeRecipients.length, EMAIL_SHARE_RECIPIENT_LIMIT)
        ? new Set()
        : defaultSelectedIds,
    )
  }

  return (
    <div
      aria-labelledby="email-share-title"
      aria-describedby="email-share-description"
      aria-modal="true"
      className="fixed inset-0 z-[120] flex items-center justify-center bg-slate-950/35 p-4 backdrop-blur-[3px]"
      onMouseDown={(event) => {
        if (event.currentTarget === event.target && !share.isPending) onClose()
      }}
      role="dialog"
    >
      <div
        className="flex max-h-[min(44rem,calc(100dvh-2rem))] w-full max-w-xl flex-col overflow-hidden rounded-[1.75rem] border border-white/70 bg-white shadow-[0_28px_90px_rgb(15_23_42/28%)]"
        ref={dialogRef}
        tabIndex={-1}
      >
        <EmailShareDialogHeader isPending={share.isPending} onClose={onClose} />
        <div className="min-h-0 flex-1 overflow-y-auto">
          {recipients.isLoading ? (
            <EmailRecipientsLoading />
          ) : recipients.isError ? (
            <EmailRecipientsError
              message={getErrorMessage(recipients.error)}
              onRetry={() => void recipients.refetch()}
            />
          ) : activeRecipients.length === 0 ? (
            <EmailRecipientsEmpty onClose={onClose} />
          ) : (
            <EmailRecipientSelector
              deliveries={share.data?.deliveries}
              disabled={share.isPending}
              onToggle={toggleRecipient}
              onToggleAll={toggleAll}
              recipients={activeRecipients}
              selectedIds={selectedIds}
            />
          )}
        </div>
        {activeRecipients.length > 0 && !recipients.isError && (
          <EmailShareFooter
            errorMessage={share.isError ? getErrorMessage(share.error) : undefined}
            isPending={share.isPending}
            onClose={onClose}
            onSend={() => share.mutate([...selectedIds])}
            receipt={share.data}
            selectedCount={selectedIds.size}
          />
        )}
      </div>
    </div>
  )
}

export default EmailShareDialog
