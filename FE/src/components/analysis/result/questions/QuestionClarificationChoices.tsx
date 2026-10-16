import type { WorkbookQuestionAnswer } from '@/api/analysis'
import { getClarificationOptions } from '@/components/analysis/result/questions/questionClarification'

export interface QuestionClarificationProps {
  answer: WorkbookQuestionAnswer
  choicesDisabled?: boolean
  onChoose?: (answer: WorkbookQuestionAnswer, optionId: string) => Promise<boolean>
}

const QuestionClarificationChoices = ({
  answer,
  choicesDisabled = true,
  onChoose,
}: QuestionClarificationProps) => {
  const options = getClarificationOptions(answer)
  if (!options.length) return null
  return (
    <fieldset className="mt-4" disabled={choicesDisabled || !onChoose}>
      <legend className="text-xs font-extrabold text-slate-700">
        질문할 항목을 선택해 주세요
      </legend>
      <p className="mt-1 text-xs leading-5 text-slate-500">
        선택하면 해당 원본 범위로 질문을 이어갑니다.
      </p>
      <div className="mt-2 grid gap-2 sm:grid-cols-2">
        {options.map((option) => (
          <button
            className="rounded-2xl border border-brand-200 bg-white px-3 py-2.5 text-left hover:border-brand-400 hover:bg-brand-50 focus-visible:outline-2 focus-visible:outline-brand-500 disabled:cursor-not-allowed disabled:opacity-50"
            key={option.id}
            onClick={() => void onChoose?.(answer, option.id)}
            type="button"
          >
            <span className="block break-words text-sm font-extrabold text-brand-700">
              {option.label}
            </span>
            {option.scope && (
              <span className="mt-1 block break-words text-xs text-slate-600">
                {option.scope}
              </span>
            )}
            {option.details && (
              <span className="mt-1 block whitespace-pre-wrap break-words text-xs leading-5 text-slate-500">
                {option.details}
              </span>
            )}
          </button>
        ))}
      </div>
    </fieldset>
  )
}

export default QuestionClarificationChoices
