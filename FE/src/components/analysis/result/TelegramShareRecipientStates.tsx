import { CircleAlert, LoaderCircle, MessageCircleMore, Settings2 } from 'lucide-react'
import { Link } from 'react-router-dom'

import { ROUTES } from '@/constants/navigation'

export const TelegramRecipientsLoading = () => (
  <div className="flex min-h-72 items-center justify-center gap-2 text-sm font-medium text-slate-400">
    <LoaderCircle className="animate-spin text-brand-500" size={18} />
    수신자 목록을 불러오는 중
  </div>
)

export const TelegramRecipientsError = ({
  message,
  onRetry,
}: {
  message: string
  onRetry: () => void
}) => (
  <div className="flex min-h-72 flex-col items-center justify-center px-7 text-center">
    <span className="grid size-12 place-items-center rounded-2xl bg-red-50 text-red-600">
      <CircleAlert size={21} />
    </span>
    <p className="mt-4 text-sm font-extrabold text-slate-800">
      수신자 목록을 불러오지 못했습니다
    </p>
    <p className="mt-1 max-w-sm text-xs leading-5 text-slate-400">{message}</p>
    <button
      className="mt-4 h-9 rounded-xl bg-slate-100 px-4 text-xs font-bold text-slate-600 transition hover:bg-slate-200"
      onClick={onRetry}
      type="button"
    >
      다시 불러오기
    </button>
  </div>
)

export const TelegramRecipientsEmpty = ({ onClose }: { onClose: () => void }) => (
  <div className="flex min-h-80 flex-col items-center justify-center px-7 text-center">
    <span className="grid size-14 place-items-center rounded-2xl bg-brand-50 text-brand-600">
      <MessageCircleMore size={24} />
    </span>
    <p className="mt-5 text-base font-extrabold text-slate-900">
      연결된 텔레그램 수신자가 없습니다
    </p>
    <p className="mt-2 max-w-sm text-sm leading-6 text-slate-500">
      먼저 초대 링크를 보내 수신자를 연결하면 이곳에서 선택해 전송할 수 있습니다.
    </p>
    <Link
      className="button-primary mt-5 inline-flex gap-2"
      onClick={onClose}
      to={ROUTES.telegramRecipients}
    >
      <Settings2 size={16} /> 수신자 설정으로 이동
    </Link>
  </div>
)
