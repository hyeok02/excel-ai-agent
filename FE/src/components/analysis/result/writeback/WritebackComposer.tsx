import { CornerDownLeft, Send } from 'lucide-react'
import type { RefObject } from 'react'

import PromptComposerFrame, {
  promptComposerActionClassName,
  promptComposerTextareaClassName,
} from '@/components/analysis/common/PromptComposerFrame'

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
    <PromptComposerFrame
      action={
        <button
          className={promptComposerActionClassName}
          disabled={disabled || instruction.trim().length < 2 || isPending}
          type="submit"
        >
          <Send size={15} /> {isPending ? '원본 셀 확인 중…' : '변경 제안 만들기'}
        </button>
      }
      hint={
        <>
          <CornerDownLeft aria-hidden="true" size={12} /> Enter로 변경 제안 · Shift+Enter
          줄바꿈
        </>
      }
    >
      <textarea
        className={`${promptComposerTextareaClassName} min-h-20 resize-y`}
        disabled={disabled}
        maxLength={1000}
        onChange={(event) => onChange(event.target.value)}
        onKeyDown={(event) => {
          if (
            event.key === 'Enter' &&
            !event.shiftKey &&
            !event.nativeEvent.isComposing
          ) {
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
    </PromptComposerFrame>
  </form>
)

export default WritebackComposer
