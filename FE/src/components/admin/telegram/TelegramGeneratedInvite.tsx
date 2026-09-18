import { Check, Copy, ExternalLink } from 'lucide-react'

import type { CreatedTelegramInvitation } from '@/api/telegram'
import { formatTelegramDate } from '@/components/admin/telegram/telegramPresentation'

interface TelegramGeneratedInviteProps {
  copied: boolean
  invitation: CreatedTelegramInvitation
  onCopy: () => void
}

const TelegramGeneratedInvite = ({
  copied,
  invitation,
  onCopy,
}: TelegramGeneratedInviteProps) => (
  <section className="page-reveal rounded-[1.5rem] border border-emerald-200 bg-emerald-50/70 p-5 shadow-sm md:p-6">
    <div className="flex flex-wrap items-start justify-between gap-4">
      <div className="flex min-w-0 items-start gap-3">
        <span className="grid size-10 shrink-0 place-items-center rounded-xl bg-emerald-100 text-emerald-700">
          <Check size={18} strokeWidth={2.5} />
        </span>
        <div className="min-w-0">
          <h2 className="text-sm font-extrabold text-emerald-950">
            초대 링크가 준비됐습니다
          </h2>
          <p className="mt-1 text-xs leading-5 text-emerald-700">
            {invitation.label || '새 텔레그램 수신자'} ·{' '}
            {formatTelegramDate(invitation.expiresAt)}까지 유효
          </p>
        </div>
      </div>
      <div className="flex shrink-0 gap-2">
        <button
          className="inline-flex h-10 items-center gap-2 rounded-xl border border-emerald-200 bg-white px-3.5 text-xs font-bold text-emerald-700 shadow-sm transition hover:bg-emerald-50"
          onClick={onCopy}
          type="button"
        >
          {copied ? <Check size={15} /> : <Copy size={15} />}
          {copied ? '복사됨' : '링크 복사'}
        </button>
        <a
          className="inline-flex h-10 items-center gap-2 rounded-xl bg-emerald-600 px-3.5 text-xs font-bold text-white shadow-sm transition hover:bg-emerald-700"
          href={invitation.inviteUrl}
          rel="noreferrer"
          target="_blank"
        >
          <ExternalLink size={15} /> 열어보기
        </a>
      </div>
    </div>
    <div className="mt-4 truncate rounded-xl border border-emerald-200/80 bg-white/80 px-4 py-3 font-mono text-xs text-emerald-800">
      {invitation.inviteUrl}
    </div>
  </section>
)

export default TelegramGeneratedInvite
