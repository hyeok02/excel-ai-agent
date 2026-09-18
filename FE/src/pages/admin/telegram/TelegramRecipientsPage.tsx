import { CircleAlert, RefreshCw } from 'lucide-react'
import { type FormEvent, useMemo, useState } from 'react'

import TelegramGeneratedInvite from '@/components/admin/telegram/TelegramGeneratedInvite'
import TelegramInvitationList from '@/components/admin/telegram/TelegramInvitationList'
import TelegramInviteHero from '@/components/admin/telegram/TelegramInviteHero'
import TelegramRecipientList from '@/components/admin/telegram/TelegramRecipientList'
import useTelegramRecipientManagement from '@/hooks/telegram/useTelegramRecipientManagement'
import { getErrorMessage } from '@/utils/apiClient'

const TelegramRecipientsPage = () => {
  const {
    createInvitation,
    invitations,
    recipients,
    refresh,
    removeRecipient,
    revokeInvitation,
  } = useTelegramRecipientManagement()
  const [label, setLabel] = useState('')
  const [copied, setCopied] = useState(false)
  const connectedRecipients = recipients.data ?? []
  const pendingInvitations = useMemo(
    () => (invitations.data ?? []).filter((invitation) => invitation.status === 'ACTIVE'),
    [invitations.data],
  )
  const hasQueryError = recipients.isError || invitations.isError
  const isRefreshing = recipients.isFetching || invitations.isFetching
  const actionError = removeRecipient.error ?? revokeInvitation.error

  const handleCreate = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    setCopied(false)
    createInvitation.mutate(label.trim() || undefined, {
      onSuccess: () => setLabel(''),
    })
  }

  const copyInvite = async () => {
    const url = createInvitation.data?.inviteUrl
    if (!url) return
    await navigator.clipboard.writeText(url)
    setCopied(true)
    window.setTimeout(() => setCopied(false), 2_000)
  }

  return (
    <div className="space-y-7">
      <div className="page-heading page-reveal">
        <div>
          <p className="eyebrow">TELEGRAM DELIVERY</p>
          <h1 className="page-title">텔레그램 수신자</h1>
          <p className="page-description">
            초대 링크로 수신자를 연결하고, Excel 분석 결과를 보낼 대상을 관리합니다.
          </p>
        </div>
        <div className="flex items-center gap-2">
          <button
            aria-label="수신자와 초대 목록 새로고침"
            className="grid size-10 place-items-center rounded-xl border border-slate-200 bg-white text-slate-500 shadow-sm transition hover:border-brand-200 hover:text-brand-600 disabled:cursor-wait disabled:opacity-60"
            disabled={isRefreshing}
            onClick={() => void refresh()}
            type="button"
          >
            <RefreshCw className={isRefreshing ? 'animate-spin' : undefined} size={16} />
          </button>
          <div className="status-pill" data-status={hasQueryError ? 'error' : 'success'}>
            <span /> 연결 {connectedRecipients.length}명
          </div>
        </div>
      </div>

      {hasQueryError && (
        <ErrorNotice
          detail={getErrorMessage(recipients.error ?? invitations.error)}
          title="텔레그램 설정을 불러오지 못했습니다."
        />
      )}

      <TelegramInviteHero
        isCreating={createInvitation.isPending}
        label={label}
        onLabelChange={setLabel}
        onSubmit={handleCreate}
      />

      {createInvitation.data && (
        <TelegramGeneratedInvite
          copied={copied}
          invitation={createInvitation.data}
          onCopy={() => void copyInvite()}
        />
      )}
      {createInvitation.isError && (
        <ErrorNotice
          detail={getErrorMessage(createInvitation.error)}
          title="초대 링크를 만들지 못했습니다."
        />
      )}

      <div className="grid items-start gap-6 xl:grid-cols-[1.35fr_0.9fr]">
        <TelegramRecipientList
          isLoading={recipients.isLoading}
          isRemoving={(id) =>
            removeRecipient.isPending && removeRecipient.variables === id
          }
          onRemove={(id) => removeRecipient.mutate(id)}
          recipients={connectedRecipients}
        />
        <TelegramInvitationList
          invitations={pendingInvitations}
          isLoading={invitations.isLoading}
          isRevoking={(id) =>
            revokeInvitation.isPending && revokeInvitation.variables === id
          }
          onRevoke={(id) => revokeInvitation.mutate(id)}
        />
      </div>

      {actionError && (
        <ErrorNotice
          detail={getErrorMessage(actionError)}
          title="요청을 처리하지 못했습니다."
        />
      )}
    </div>
  )
}

const ErrorNotice = ({ detail, title }: { detail: string; title: string }) => (
  <div
    className="page-reveal flex items-start gap-3 rounded-2xl border border-red-200 bg-red-50 px-5 py-4 text-sm text-red-700"
    role="alert"
  >
    <CircleAlert className="mt-0.5 shrink-0" size={17} />
    <div>
      <p className="font-bold">{title}</p>
      <p className="mt-1 text-xs text-red-600">{detail}</p>
    </div>
  </div>
)

export default TelegramRecipientsPage
