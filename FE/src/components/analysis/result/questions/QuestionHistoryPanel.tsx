import { ChevronDown } from 'lucide-react'

import type { WorkbookQuestionAnswer } from '@/api/analysis'
import QuestionAnswerCard from '@/components/analysis/result/questions/QuestionAnswerCard'
import type { QuestionClarificationProps } from '@/components/analysis/result/questions/QuestionClarificationChoices'

interface QuestionHistoryPanelProps extends Omit<QuestionClarificationProps, 'answer'> {
  answers: WorkbookQuestionAnswer[]
  hasEarlier: boolean
  isLoading: boolean
  errorMessage: string | null
  onLoadEarlier: () => Promise<void>
}

const QuestionHistoryPanel = ({
  answers,
  hasEarlier,
  isLoading,
  errorMessage,
  onLoadEarlier,
  choicesDisabled,
  onChoose,
}: QuestionHistoryPanelProps) => {
  const previousAnswers = answers.slice(0, -1).reverse()
  if (!previousAnswers.length && !hasEarlier) return null
  return (
    <details className="group mt-3 rounded-2xl border border-slate-200 bg-white/70 p-3">
      <summary className="flex cursor-pointer list-none items-center justify-center gap-2 text-xs font-extrabold text-slate-600">
        이전 질문 {previousAnswers.length}개 보기
        {hasEarlier && ' · 더 있음'}
        <ChevronDown
          aria-hidden="true"
          className="transition group-open:rotate-180"
          size={15}
        />
      </summary>
      <div className="mt-3 space-y-3 border-t border-slate-100 pt-3">
        {previousAnswers.map((answer, index) => (
          <QuestionAnswerCard
            answer={answer}
            choicesDisabled={choicesDisabled}
            key={`${answer.question}-${previousAnswers.length - index}`}
            onChoose={onChoose}
          />
        ))}
        {errorMessage && (
          <p className="text-center text-xs text-amber-800" role="alert">
            이전 대화를 더 불러오지 못했습니다. 다시 시도해 주세요. {errorMessage}
          </p>
        )}
        {hasEarlier && (
          <button
            className="w-full rounded-xl border border-slate-200 px-3 py-2 text-xs font-bold text-slate-600 hover:bg-slate-50 disabled:opacity-50"
            disabled={isLoading}
            onClick={() => void onLoadEarlier()}
            type="button"
          >
            {isLoading ? '불러오는 중…' : '이전 대화 더 보기'}
          </button>
        )}
      </div>
    </details>
  )
}

export default QuestionHistoryPanel
