import { useMutation } from '@tanstack/react-query'
import { Check, LoaderCircle, Send, TriangleAlert } from 'lucide-react'

import { shareAnalysisToTelegram } from '@/api/analysis'
import { getErrorMessage } from '@/utils/apiClient'

interface TelegramShareButtonProps {
  analysisId: string
}

const TelegramShareButton = ({ analysisId }: TelegramShareButtonProps) => {
  const share = useMutation({
    mutationFn: () => shareAnalysisToTelegram(analysisId),
  })
  const feedback = share.isError
    ? getErrorMessage(share.error)
    : share.isSuccess
      ? '분석 요약을 텔레그램으로 보냈습니다.'
      : ''
  const Icon = share.isPending
    ? LoaderCircle
    : share.isSuccess
      ? Check
      : share.isError
        ? TriangleAlert
        : Send
  const label = share.isPending
    ? '전송 중'
    : share.isSuccess
      ? '전송 완료'
      : share.isError
        ? '전송 실패'
        : '텔레그램'
  const stateClass = share.isError
    ? 'border-red-200 bg-red-50 text-red-700 hover:bg-red-100'
    : share.isSuccess
      ? 'border-emerald-200 bg-emerald-50 text-emerald-700 hover:bg-emerald-100'
      : 'border-sky-200 bg-sky-50 text-sky-700 hover:bg-sky-100'

  return (
    <div className="inline-flex">
      <button
        className={`inline-flex h-10 min-w-24 items-center justify-center gap-1.5 rounded-xl border px-3 text-xs font-extrabold shadow-sm transition focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-sky-500 disabled:cursor-wait disabled:opacity-70 ${stateClass}`}
        disabled={share.isPending}
        onClick={() => share.mutate()}
        title={feedback || '분석 결과를 설정된 텔레그램 채팅방으로 보냅니다.'}
        type="button"
      >
        <Icon
          aria-hidden="true"
          className={share.isPending ? 'animate-spin' : undefined}
          size={15}
        />
        {label}
      </button>
      <span
        aria-live="polite"
        className="sr-only"
        role={share.isError ? 'alert' : 'status'}
      >
        {feedback}
      </span>
    </div>
  )
}

export default TelegramShareButton
