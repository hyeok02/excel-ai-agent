import { CircleAlert, CornerDownLeft, LoaderCircle, Send } from 'lucide-react'
import { useState } from 'react'

const SUGGESTIONS = [
  '이 파일에서 가장 중요한 수치와 기준 시점을 알려줘',
  '검토해야 할 수식 오류나 외부 참조가 있어?',
  '핵심 내용을 확인할 원본 셀 위치를 알려줘',
]

interface QuestionComposerProps {
  disabled?: boolean
  isPending: boolean
  onAsk: (question: string) => boolean
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
  const submit = (value = question) => {
    if (disabled) return
    if (onAsk(value)) setQuestion('')
  }

  return (
    <div>
      <div className="rounded-2xl border border-brand-200 bg-white p-2 shadow-sm focus-within:ring-2 focus-within:ring-brand-100">
        <textarea
          aria-label="Excel에 질문"
          className="min-h-20 w-full resize-none bg-transparent px-3 py-2 text-sm leading-6 text-slate-800 outline-none placeholder:text-slate-400"
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
              submit()
            }
          }}
          placeholder={
            disabled
              ? '원본 파일 보관기간이 지나 질문할 수 없습니다.'
              : '예: 2024년 매출이 가장 높은 항목과 근거 셀을 알려줘'
          }
          value={question}
        />
        <div className="flex items-center justify-between gap-3 border-t border-slate-100 px-2 pt-2">
          <span className="hidden items-center gap-1 text-[11px] text-slate-400 sm:flex">
            <CornerDownLeft size={12} /> Enter로 질문 · Shift+Enter 줄바꿈
          </span>
          <button
            className="ml-auto inline-flex h-9 items-center gap-2 rounded-xl bg-brand-600 px-4 text-xs font-extrabold text-white hover:bg-brand-700 disabled:bg-slate-300"
            disabled={disabled || isPending || question.trim().length < 2}
            onClick={() => submit()}
            type="button"
          >
            {isPending ? (
              <LoaderCircle className="animate-spin" size={15} />
            ) : (
              <Send size={15} />
            )}
            {isPending ? '근거 확인 중' : '질문하기'}
          </button>
        </div>
      </div>
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
        {SUGGESTIONS.map((suggestion) => (
          <button
            className="rounded-full border border-brand-100 bg-brand-50 px-3 py-1.5 text-xs font-bold text-brand-700 hover:bg-brand-100 disabled:opacity-50"
            disabled={disabled || isPending}
            key={suggestion}
            onClick={() => submit(suggestion)}
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
