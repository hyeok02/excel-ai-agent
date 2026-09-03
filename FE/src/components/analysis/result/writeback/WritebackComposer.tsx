import { CornerDownLeft, Send } from 'lucide-react'
import type { RefObject } from 'react'

interface WritebackComposerProps {
  disabled?: boolean
  instruction: string
  isPending: boolean
  onChange: (value: string) => void
  onSubmit: () => void
  textareaRef: RefObject<HTMLTextAreaElement | null>
}

const WritebackComposer = ({
  disabled = false,
  instruction,
  isPending,
  onChange,
  onSubmit,
  textareaRef,
}: WritebackComposerProps) => (
  <form
    className="mt-5"
    onSubmit={(event) => {
      event.preventDefault()
      onSubmit()
    }}
  >
    <textarea
      className="min-h-28 w-full resize-y rounded-2xl border border-slate-200 bg-white p-4 text-sm text-slate-800 shadow-sm outline-none transition focus:border-brand-400 focus:ring-4 focus:ring-brand-50"
      disabled={disabled}
      maxLength={1000}
      onChange={(event) => onChange(event.target.value)}
      onKeyDown={(event) => {
        if (event.key === 'Enter' && !event.shiftKey && !event.nativeEvent.isComposing) {
          event.preventDefault()
          event.currentTarget.form?.requestSubmit()
        }
      }}
      placeholder={
        disabled
          ? '원본 파일 보관기간이 지나 수정할 수 없습니다.'
          : '예: 매출현황 B2:B20을 12로 바꾸고, 요약 D2 수식을 =SUM(B2:C2)로 변경해줘'
      }
      ref={textareaRef}
      value={instruction}
    />
    <div className="mt-2 flex flex-wrap items-center justify-between gap-3">
      <p className="flex items-center gap-1 text-xs font-semibold text-slate-400">
        <CornerDownLeft aria-hidden="true" size={13} /> Enter로 변경 제안 · Shift+Enter
        줄바꿈
      </p>
      <button
        className="inline-flex items-center gap-2 rounded-xl bg-brand-600 px-4 py-2.5 text-sm font-extrabold text-white shadow-sm transition hover:bg-brand-700 disabled:cursor-not-allowed disabled:bg-slate-300"
        disabled={disabled || instruction.trim().length < 2 || isPending}
        type="submit"
      >
        <Send size={16} /> {isPending ? '원본 셀 확인 중…' : '변경 제안 만들기'}
      </button>
    </div>
  </form>
)

export default WritebackComposer
