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
        ? '다시 전송'
        : '텔레그램'

  return (
    <div className="flex flex-col items-end gap-1">
      <button
        className="inline-flex h-10 items-center gap-1.5 rounded-xl border border-sky-200 bg-sky-50 px-3 text-xs font-extrabold text-sky-700 shadow-sm transition hover:bg-sky-100 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-sky-500 disabled:cursor-wait disabled:opacity-70"
        disabled={share.isPending}
        onClick={() => share.mutate()}
        title="분석 결과를 설정된 텔레그램 채팅방으로 보냅니다."
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
        className={`max-w-52 text-right text-[11px] font-semibold ${
          share.isError ? 'text-red-600' : 'text-emerald-600'
        }`}
        role={share.isError ? 'alert' : 'status'}
      >
        {share.isError
          ? getErrorMessage(share.error)
          : share.isSuccess
            ? '분석 요약을 보냈습니다.'
            : ''}
      </span>
    </div>
  )
}

export default TelegramShareButton
