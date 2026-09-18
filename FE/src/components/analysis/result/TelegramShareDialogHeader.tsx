import { Send, X } from 'lucide-react'

interface TelegramShareDialogHeaderProps {
  isPending: boolean
  onClose: () => void
}

const TelegramShareDialogHeader = ({
  isPending,
  onClose,
}: TelegramShareDialogHeaderProps) => (
  <div className="relative overflow-hidden border-b border-brand-100 bg-gradient-to-br from-brand-700 via-brand-600 to-sky-500 px-6 py-6 text-white">
    <div className="pointer-events-none absolute -right-12 -top-14 size-40 rounded-full border border-white/15 bg-white/5" />
    <div className="relative flex items-start gap-4">
      <span className="grid size-11 shrink-0 place-items-center rounded-2xl border border-white/20 bg-white/15 shadow-sm backdrop-blur">
        <Send size={19} />
      </span>
      <div className="min-w-0 flex-1">
        <p className="text-[0.65rem] font-extrabold tracking-[0.14em] text-blue-100">
          TELEGRAM DELIVERY
        </p>
        <h2
          className="mt-1 text-xl font-extrabold tracking-[-0.025em]"
          id="telegram-share-title"
        >
          분석 결과 보내기
        </h2>
        <p
          className="mt-1.5 text-xs leading-5 text-blue-100"
          id="telegram-share-description"
        >
          전송할 텔레그램 수신자를 선택하세요.
        </p>
      </div>
      <button
        aria-label="텔레그램 전송 창 닫기"
        className="grid size-9 shrink-0 place-items-center rounded-xl text-blue-100 transition hover:bg-white/15 hover:text-white disabled:cursor-wait disabled:opacity-60"
        disabled={isPending}
        onClick={onClose}
        type="button"
      >
        <X size={18} />
      </button>
    </div>
  </div>
)

export default TelegramShareDialogHeader
