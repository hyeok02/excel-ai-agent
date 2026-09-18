import { Check, LoaderCircle, MessageCircleMore, Trash2, UsersRound } from 'lucide-react'
import { useState } from 'react'

import type { TelegramRecipient } from '@/api/telegram'
import {
  TelegramEmptyState,
  TelegramLoadingState,
} from '@/components/admin/telegram/TelegramPanelStates'
import {
  formatTelegramDate,
  getRecipientStatus,
} from '@/components/admin/telegram/telegramPresentation'

interface TelegramRecipientListProps {
  isLoading: boolean
  isRemoving: (recipientId: string) => boolean
  onRemove: (recipientId: string) => void
  recipients: TelegramRecipient[]
}

const TelegramRecipientList = ({
  isLoading,
  isRemoving,
  onRemove,
  recipients,
}: TelegramRecipientListProps) => {
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
    <section className="panel page-reveal page-reveal-delay-1 overflow-hidden">
      <div className="flex items-start justify-between gap-4 border-b border-slate-100 px-6 py-5">
        <div>
          <h2 className="section-title">연결된 수신자</h2>
          <p className="section-description">
            분석 결과를 받을 수 있는 텔레그램 계정입니다.
          </p>
        </div>
        <span className="inline-flex shrink-0 items-center gap-1.5 rounded-full bg-brand-50 px-2.5 py-1 text-xs font-extrabold text-brand-700">
          <UsersRound size={13} /> {recipients.length}명
        </span>
      </div>

      {isLoading ? (
        <TelegramLoadingState label="수신자 목록을 불러오는 중" />
      ) : recipients.length === 0 ? (
        <TelegramEmptyState
          description="위에서 초대 링크를 만들어 첫 수신자를 연결해 보세요."
          icon={<MessageCircleMore size={21} />}
          title="연결된 수신자가 없습니다"
        />
      ) : (
        <div className="divide-y divide-slate-100">
          {recipients.map((recipient) => {
            const status = getRecipientStatus(recipient.status)
            const isConfirming = confirmingId === recipient.id
            const removing = isRemoving(recipient.id)
            return (
              <div
                className="flex flex-wrap items-center gap-4 px-6 py-4 transition hover:bg-slate-50/60"
                key={recipient.id}
              >
                <span className="grid size-11 shrink-0 place-items-center rounded-2xl bg-gradient-to-br from-brand-50 to-sky-100 text-sm font-extrabold text-brand-700">
                  {recipient.displayName.slice(0, 1).toUpperCase()}
                </span>
                <div className="min-w-0 flex-1">
                  <div className="flex flex-wrap items-center gap-2">
                    <p className="truncate text-sm font-extrabold text-slate-900">
                      {recipient.displayName}
                    </p>
                    <span
                      className={`inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-[0.65rem] font-bold ${status.badgeClass}`}
                    >
                      <span className={`size-1 rounded-full ${status.dotClass}`} />
                      {status.label}
                    </span>
                  </div>
                  <p className="mt-1 truncate text-xs text-slate-400">
                    {recipient.username ? `@${recipient.username}` : '사용자명 비공개'} ·{' '}
                    {formatTelegramDate(recipient.connectedAt)} 연결
                  </p>
                </div>
                <div className="ml-auto flex items-center gap-2">
                  {isConfirming && (
                    <button
                      className="h-9 rounded-lg px-2.5 text-xs font-bold text-slate-500 transition hover:bg-slate-100"
                      onClick={() => setConfirmingId(null)}
                      type="button"
                    >
                      취소
                    </button>
                  )}
                  <button
                    className={
                      isConfirming
                        ? 'inline-flex h-9 items-center gap-1.5 rounded-lg bg-red-600 px-3 text-xs font-bold text-white transition hover:bg-red-700'
                        : 'inline-flex h-9 items-center gap-1.5 rounded-lg border border-slate-200 bg-white px-3 text-xs font-bold text-slate-500 transition hover:border-red-200 hover:bg-red-50 hover:text-red-600'
                    }
                    disabled={removing}
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
                    {isConfirming ? '연결 해제 확인' : '연결 해제'}
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

export default TelegramRecipientList
