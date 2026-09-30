import { Check, CircleAlert, LoaderCircle, Mail, Trash2, UsersRound } from 'lucide-react'
import { useState } from 'react'

import type { EmailRecipient } from '@/api/email'
import {
  EmailEmptyState,
  EmailLoadingState,
} from '@/components/admin/email/EmailPanelStates'
import { formatEmailDate } from '@/components/admin/email/emailPresentation'

interface EmailRecipientListProps {
  isError: boolean
  isLoading: boolean
  isRemovalPending: boolean
  isRemoving: (recipientId: string) => boolean
  onRemove: (recipientId: string) => void
  recipients: EmailRecipient[]
}

const EmailRecipientList = ({
  isError,
  isLoading,
  isRemovalPending,
  isRemoving,
  onRemove,
  recipients,
}: EmailRecipientListProps) => {
  const [confirmingId, setConfirmingId] = useState<string | null>(null)

  const requestRemove = (recipientId: string) => {
    if (confirmingId !== recipientId) {
      setConfirmingId(recipientId)
      return
    }
    onRemove(recipientId)
    setConfirmingId(null)
  }

  return (
    <section className="panel page-reveal page-reveal-delay-2 overflow-hidden">
      <div className="flex items-start justify-between gap-4 border-b border-slate-100 px-6 py-5">
        <div>
          <h2 className="section-title">등록된 수신자</h2>
          <p className="section-description">
            분석 결과를 받을 수 있는 이메일 주소입니다.
          </p>
        </div>
        <span className="inline-flex shrink-0 items-center gap-1.5 rounded-full bg-brand-50 px-2.5 py-1 text-xs font-extrabold text-brand-700">
          <UsersRound size={13} /> {recipients.length}명
        </span>
      </div>

      {isLoading ? (
        <EmailLoadingState label="수신자 목록을 불러오는 중" />
      ) : isError ? (
        <EmailEmptyState
          description="위의 새로고침 버튼을 눌러 다시 시도해 주세요."
          icon={<CircleAlert size={21} />}
          title="수신자 목록을 표시할 수 없습니다"
        />
      ) : recipients.length === 0 ? (
        <EmailEmptyState
          description="위에서 이메일 주소를 입력해 첫 수신자를 등록해 보세요."
          icon={<Mail size={21} />}
          title="등록된 수신자가 없습니다"
        />
      ) : (
        <div className="divide-y divide-slate-100">
          {recipients.map((recipient) => {
            const displayName = recipient.displayName.trim() || recipient.email
            const isConfirming = confirmingId === recipient.id
            const removing = isRemoving(recipient.id)
            return (
              <div
                className="flex flex-wrap items-center gap-4 px-6 py-4 transition hover:bg-slate-50/60"
                key={recipient.id}
              >
                <span className="grid size-11 shrink-0 place-items-center rounded-2xl bg-gradient-to-br from-brand-50 to-sky-100 text-sm font-extrabold text-brand-700">
                  {displayName.slice(0, 1).toUpperCase()}
                </span>
                <div className="min-w-0 flex-1">
                  <div className="flex flex-wrap items-center gap-2">
                    <p className="truncate text-sm font-extrabold text-slate-900">
                      {displayName}
                    </p>
                    <span className="inline-flex items-center gap-1 rounded-full bg-emerald-50 px-2 py-0.5 text-[0.65rem] font-bold text-emerald-700">
                      <span className="size-1 rounded-full bg-emerald-500" /> 수신 가능
                    </span>
                  </div>
                  <p className="mt-1 truncate text-xs text-slate-400">
                    {recipient.email} · {formatEmailDate(recipient.createdAt)} 등록
                  </p>
                </div>
                <div className="ml-auto flex items-center gap-2">
                  {isConfirming && (
                    <button
                      aria-label={`${recipient.email} 삭제 확인 취소`}
                      className="h-9 rounded-lg px-2.5 text-xs font-bold text-slate-500 transition hover:bg-slate-100 disabled:cursor-wait disabled:opacity-60"
                      disabled={isRemovalPending}
                      onClick={() => setConfirmingId(null)}
                      type="button"
                    >
                      취소
                    </button>
                  )}
                  <button
                    aria-label={
                      isConfirming
                        ? `${recipient.email} 삭제 확인`
                        : `${recipient.email} 삭제`
                    }
                    className={
                      isConfirming
                        ? 'inline-flex h-9 items-center gap-1.5 rounded-lg border border-red-200 bg-red-50 px-3 text-xs font-extrabold text-red-800 shadow-sm transition hover:border-red-300 hover:bg-red-100 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-red-300 focus-visible:ring-offset-1 disabled:cursor-wait disabled:opacity-60'
                        : 'inline-flex h-9 items-center gap-1.5 rounded-lg border border-slate-200 bg-white px-3 text-xs font-bold text-slate-500 transition hover:border-red-200 hover:bg-red-50 hover:text-red-600 disabled:cursor-wait disabled:opacity-60'
                    }
                    disabled={isRemovalPending}
                    onClick={() => requestRemove(recipient.id)}
                    type="button"
                  >
                    {removing ? (
                      <LoaderCircle className="animate-spin" size={14} />
                    ) : isConfirming ? (
                      <Check size={14} />
                    ) : (
                      <Trash2 size={14} />
                    )}
                    {removing ? '삭제 중…' : isConfirming ? '삭제 확인' : '삭제'}
                  </button>
                </div>
              </div>
            )
          })}
        </div>
      )}
    </section>
  )
}

export default EmailRecipientList
