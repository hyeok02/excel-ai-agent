import { CheckCircle2, CircleAlert, RefreshCw } from 'lucide-react'
import { type FormEvent, useState } from 'react'

import EmailRecipientHero from '@/components/admin/email/EmailRecipientHero'
import EmailRecipientList from '@/components/admin/email/EmailRecipientList'
import useEmailRecipientManagement from '@/hooks/email/useEmailRecipientManagement'
import { getErrorMessage } from '@/utils/apiClient'

const EmailRecipientsPage = () => {
  const { createRecipient, recipients, refresh, removeRecipient } =
    useEmailRecipientManagement()
  const [displayName, setDisplayName] = useState('')
  const [email, setEmail] = useState('')
  const registeredRecipients = recipients.data ?? []

  const changeDisplayName = (value: string) => {
    if (createRecipient.isSuccess || createRecipient.isError) createRecipient.reset()
    setDisplayName(value)
  }

  const changeEmail = (value: string) => {
    if (createRecipient.isSuccess || createRecipient.isError) createRecipient.reset()
    setEmail(value)
  }

  const handleCreate = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    const normalizedEmail = email.trim()
    if (!normalizedEmail) return

    const normalizedName = displayName.trim()
    createRecipient.mutate(
      {
        email: normalizedEmail,
        ...(normalizedName ? { displayName: normalizedName } : {}),
      },
      {
        onSuccess: () => {
          setDisplayName('')
          setEmail('')
        },
      },
    )
  }

  return (
    <div className="space-y-7">
      <div className="page-heading page-reveal">
        <div>
          <p className="eyebrow">EMAIL DELIVERY</p>
          <h1 className="page-title">이메일 수신자</h1>
          <p className="page-description">
            이메일 주소를 등록하고, Excel 분석 결과를 보낼 대상을 관리합니다.
          </p>
        </div>
        <div className="flex items-center gap-2">
          <button
            aria-label="이메일 수신자 목록 새로고침"
            className="grid size-10 place-items-center rounded-xl border border-slate-200 bg-white text-slate-500 shadow-sm transition hover:border-brand-200 hover:text-brand-600 disabled:cursor-wait disabled:opacity-60"
            disabled={recipients.isFetching}
            onClick={() => void refresh()}
            type="button"
          >
            <RefreshCw
              className={recipients.isFetching ? 'animate-spin' : undefined}
              size={16}
            />
          </button>
          <div
            aria-live="polite"
            className="status-pill"
            data-status={recipients.isError ? 'error' : 'success'}
          >
            <span /> 등록 {registeredRecipients.length}명
          </div>
        </div>
      </div>

      {recipients.isError && (
        <ErrorNotice
          detail={getErrorMessage(recipients.error)}
          title="이메일 수신자 목록을 불러오지 못했습니다."
        />
      )}

      <EmailRecipientHero
        displayName={displayName}
        email={email}
        isCreating={createRecipient.isPending}
        onDisplayNameChange={changeDisplayName}
        onEmailChange={changeEmail}
        onSubmit={handleCreate}
      />

      {createRecipient.isSuccess && createRecipient.data && (
        <div
          className="page-reveal flex items-start gap-3 rounded-2xl border border-emerald-200 bg-emerald-50 px-5 py-4 text-sm text-emerald-700"
          role="status"
        >
          <CheckCircle2 className="mt-0.5 shrink-0" size={17} />
          <div>
            <p className="font-bold">이메일 수신자를 등록했습니다.</p>
            <p className="mt-1 text-xs text-emerald-600">{createRecipient.data.email}</p>
          </div>
        </div>
      )}

      {createRecipient.isError && (
        <ErrorNotice
          detail={getErrorMessage(createRecipient.error)}
          title="이메일 수신자를 등록하지 못했습니다."
        />
      )}

      {removeRecipient.isError && (
        <ErrorNotice
          detail={getErrorMessage(removeRecipient.error)}
          title="이메일 수신자를 삭제하지 못했습니다."
        />
      )}

      <EmailRecipientList
        isError={recipients.isError}
        isLoading={recipients.isLoading}
        isRemovalPending={removeRecipient.isPending}
        isRemoving={(id) => removeRecipient.isPending && removeRecipient.variables === id}
        onRemove={(id) => removeRecipient.mutate(id)}
        recipients={registeredRecipients}
      />
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

export default EmailRecipientsPage
