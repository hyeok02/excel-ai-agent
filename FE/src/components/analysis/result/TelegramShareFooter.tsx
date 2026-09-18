import { CheckCircle2, CircleAlert, LoaderCircle, Send } from 'lucide-react'

import type { TelegramShareReceipt } from '@/api/telegram'

interface TelegramShareFooterProps {
  errorMessage?: string
  isPending: boolean
  onClose: () => void
  onSend: () => void
  receipt?: TelegramShareReceipt
  selectedCount: number
}

const TelegramShareFooter = ({
  errorMessage,
  isPending,
  onClose,
  onSend,
  receipt,
  selectedCount,
}: TelegramShareFooterProps) => {
  const complete = Boolean(receipt && receipt.failureCount === 0)
  const shouldRetry = Boolean(errorMessage || receipt?.failureCount)

  return (
    <div className="border-t border-slate-100 bg-slate-50/80 px-6 py-5">
      {receipt && (
        <div
          className={`mb-4 flex items-start gap-2 rounded-xl border px-3.5 py-3 text-xs font-semibold ${
            receipt.failureCount > 0
              ? 'border-amber-200 bg-amber-50 text-amber-800'
              : 'border-emerald-200 bg-emerald-50 text-emerald-700'
          }`}
          role="status"
        >
          {receipt.failureCount > 0 ? (
            <CircleAlert className="mt-0.5 shrink-0" size={15} />
          ) : (
            <CheckCircle2 className="mt-0.5 shrink-0" size={15} />
          )}
          <span>
            {receipt.successCount}명에게 전송했습니다.
            {receipt.failureCount > 0 &&
              ` ${receipt.failureCount}명은 전송하지 못했습니다.`}
          </span>
        </div>
      )}
      {errorMessage && (
        <div
          className="mb-4 flex items-start gap-2 rounded-xl border border-red-200 bg-red-50 px-3.5 py-3 text-xs font-semibold text-red-700"
          role="alert"
        >
          <CircleAlert className="mt-0.5 shrink-0" size={15} />
          <span>전송하지 못했습니다. {errorMessage}</span>
        </div>
      )}

      <div className="flex items-center justify-between gap-4">
        <p className="text-xs font-semibold text-slate-500">
          <strong className="text-slate-800">{selectedCount}명</strong> 선택됨
        </p>
        <div className="flex items-center gap-2">
          <button
            className="h-10 rounded-xl px-4 text-xs font-bold text-slate-500 transition hover:bg-slate-200/70 hover:text-slate-700"
            disabled={isPending}
            onClick={onClose}
            type="button"
          >
            {complete ? '닫기' : '취소'}
          </button>
          {!complete && (
            <button
              className="button-primary inline-flex h-10 min-w-28 gap-2 px-4 text-xs"
              disabled={selectedCount === 0 || isPending}
              onClick={onSend}
              type="button"
            >
              {isPending ? (
                <LoaderCircle className="animate-spin" size={15} />
              ) : (
                <Send size={15} />
              )}
              {isPending ? '전송 중' : shouldRetry ? '다시 전송' : '선택 전송'}
            </button>
          )}
        </div>
      </div>
    </div>
  )
}

export default TelegramShareFooter
