import { Clock3, Link2, X } from 'lucide-react'
import { useState } from 'react'

import type { TelegramInvitation } from '@/api/telegram'
import {
  TelegramEmptyState,
  TelegramLoadingState,
} from '@/components/admin/telegram/TelegramPanelStates'
import {
  formatTelegramDate,
  getInvitationStatus,
} from '@/components/admin/telegram/telegramPresentation'

interface TelegramInvitationListProps {
  invitations: TelegramInvitation[]
  isLoading: boolean
  isRevoking: (invitationId: string) => boolean
  onRevoke: (invitationId: string) => void
}

const TelegramInvitationList = ({
  invitations,
  isLoading,
  isRevoking,
  onRevoke,
}: TelegramInvitationListProps) => {
  const [confirmingId, setConfirmingId] = useState<string | null>(null)

  const requestRevoke = (invitationId: string) => {
    if (confirmingId !== invitationId) {
      setConfirmingId(invitationId)
      return
    }
    onRevoke(invitationId)
    setConfirmingId(null)
  }

  return (
    <section className="panel page-reveal page-reveal-delay-2 overflow-hidden">
      <div className="flex items-start justify-between gap-4 border-b border-slate-100 px-6 py-5">
        <div>
          <h2 className="section-title">등록 대기 중인 초대</h2>
          <p className="section-description">
            아직 텔레그램 연결을 완료하지 않은 초대입니다.
          </p>
        </div>
        <span className="inline-flex shrink-0 items-center gap-1.5 rounded-full bg-amber-50 px-2.5 py-1 text-xs font-extrabold text-amber-700">
          <Clock3 size={13} /> {invitations.length}건
        </span>
      </div>

      {isLoading ? (
        <TelegramLoadingState label="초대 목록을 불러오는 중" />
      ) : invitations.length === 0 ? (
        <TelegramEmptyState
          description="생성한 초대 링크가 이곳에 표시됩니다."
          icon={<Link2 size={21} />}
          title="대기 중인 초대가 없습니다"
        />
      ) : (
        <div className="divide-y divide-slate-100">
          {invitations.map((invitation) => {
            const status = getInvitationStatus(invitation.status)
            const isConfirming = confirmingId === invitation.id
            const revoking = isRevoking(invitation.id)
            return (
              <div className="px-6 py-4" key={invitation.id}>
                <div className="flex flex-wrap items-center gap-3">
                  <span className="grid size-10 shrink-0 place-items-center rounded-xl bg-amber-50 text-amber-600">
                    <Link2 size={17} />
                  </span>
                  <div className="min-w-0 flex-1">
                    <div className="flex flex-wrap items-center gap-2">
                      <p className="truncate text-sm font-bold text-slate-800">
                        {invitation.label || '이름 없는 초대'}
                      </p>
                      <span
                        className={`rounded-full px-2 py-0.5 text-[0.65rem] font-bold ${status.className}`}
                      >
                        {status.label}
                      </span>
                    </div>
                    <p className="mt-1 text-xs text-slate-400">
                      {formatTelegramDate(invitation.expiresAt)} 만료
                    </p>
                  </div>
                </div>
                <div className="mt-3 flex items-center justify-between gap-3 rounded-xl bg-slate-50 px-3 py-2.5">
                  <p className="text-[0.68rem] leading-4 text-slate-400">
                    링크 주소는 생성 직후에만 확인할 수 있습니다.
                  </p>
                  <div className="flex shrink-0 items-center gap-1.5">
                    {isConfirming && (
                      <button
                        aria-label="초대 취소 작업 닫기"
                        className="grid size-8 place-items-center rounded-lg text-slate-400 transition hover:bg-white hover:text-slate-600"
                        onClick={() => setConfirmingId(null)}
                        type="button"
                      >
                        <X size={14} />
                      </button>
                    )}
                    <button
                      className={
                        isConfirming
                          ? 'h-8 rounded-lg bg-red-600 px-2.5 text-[0.68rem] font-bold text-white'
                          : 'h-8 rounded-lg px-2.5 text-[0.68rem] font-bold text-slate-500 transition hover:bg-white hover:text-red-600'
                      }
                      disabled={revoking}
                      onClick={() => requestRevoke(invitation.id)}
                      type="button"
                    >
                      {revoking
                        ? '취소 중…'
                        : isConfirming
                          ? '초대 취소 확인'
                          : '초대 취소'}
                    </button>
                  </div>
                </div>
              </div>
            )
          })}
        </div>
      )}
    </section>
  )
}

export default TelegramInvitationList
