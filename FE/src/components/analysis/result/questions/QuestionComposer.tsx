import { CircleAlert, CornerDownLeft, LoaderCircle, Send } from 'lucide-react'
import { useState } from 'react'

import PromptComposerFrame, {
  promptComposerActionClassName,
  promptComposerTextareaClassName,
} from '@/components/analysis/common/PromptComposerFrame'
import { QUESTION_SUGGESTIONS } from '@/components/analysis/result/questions/questionPresentation'

interface QuestionComposerProps {
  disabled?: boolean
  isPending: boolean
  onAsk: (question: string) => Promise<boolean>
  onValidationClear: () => void
  validationMessage: string | null
}

const QuestionComposer = ({
  disabled = false,
  isPending,
  onAsk,
  onValidationClear,
  validationMessage,
}: QuestionComposerProps) => {
  const [question, setQuestion] = useState('')
  const submit = async (value = question) => {
    if (disabled) return
    setQuestion(value)
    if (await onAsk(value)) setQuestion('')
  }

  return (
    <div>
      <PromptComposerFrame
        action={
          <button
            className={promptComposerActionClassName}
            disabled={disabled || isPending || question.trim().length < 2}
            onClick={() => void submit()}
            type="button"
          >
            {isPending ? (
              <LoaderCircle aria-hidden="true" className="animate-spin" size={15} />
            ) : (
              <Send aria-hidden="true" size={15} />
            )}
            {isPending ? '답변 준비 중' : '질문하기'}
          </button>
        }
        hint={
          <>
            <CornerDownLeft size={12} /> Enter로 질문 · Shift+Enter 줄바꿈
          </>
        }
      >
        <textarea
          aria-label="Excel에 질문"
          className={`${promptComposerTextareaClassName} min-h-20 resize-none`}
          disabled={disabled || isPending}
          maxLength={1000}
          onChange={(event) => {
            setQuestion(event.target.value)
            onValidationClear()
          }}
          onKeyDown={(event) => {
            if (
              event.key === 'Enter' &&
              !event.shiftKey &&
              !event.nativeEvent.isComposing
            ) {
              event.preventDefault()
              void submit()
            }
          }}
          placeholder={
            disabled
              ? '원본 파일 보관기간이 지나 질문할 수 없습니다.'
              : '예: 이 파일에서 가장 중요한 결론은 뭐야?'
          }
          value={question}
        />
      </PromptComposerFrame>
      {validationMessage && (
        <div
          className="mt-3 flex items-start gap-2 rounded-2xl bg-amber-50 px-4 py-3 text-sm leading-6 text-amber-800"
          role="alert"
        >
          <CircleAlert className="mt-1 shrink-0" aria-hidden="true" size={16} />
          {validationMessage}
        </div>
      )}
      <div className="mt-3 flex flex-wrap gap-2">
        {QUESTION_SUGGESTIONS.map((suggestion) => (
          <button
            className="rounded-full border border-brand-100 bg-brand-50 px-3 py-1.5 text-xs font-bold text-brand-700 hover:bg-brand-100 disabled:opacity-50"
            disabled={disabled || isPending}
            key={suggestion}
            onClick={() => void submit(suggestion)}
            type="button"
          >
            {suggestion}
          </button>
        ))}
      </div>
    </div>
  )
}

export default QuestionComposer
