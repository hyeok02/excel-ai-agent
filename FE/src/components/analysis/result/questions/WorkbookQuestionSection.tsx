import { ChevronDown, MessageSquareText, TriangleAlert } from 'lucide-react'

import QuestionAnswerCard from '@/components/analysis/result/questions/QuestionAnswerCard'
import QuestionComposer from '@/components/analysis/result/questions/QuestionComposer'
import { useWorkbookQuestions } from '@/hooks/analysis/useWorkbookQuestions'

interface WorkbookQuestionSectionProps {
  analysisId: string
  sourceAvailable: boolean
}

const WorkbookQuestionSection = ({
  analysisId,
  sourceAvailable,
}: WorkbookQuestionSectionProps) => {
  const questions = useWorkbookQuestions(analysisId)
  const latestAnswer = questions.answers.at(-1)
  const previousAnswers = questions.answers.slice(0, -1).reverse()
  return (
    <section className="mt-6 overflow-hidden rounded-3xl border border-brand-200 bg-gradient-to-br from-brand-50 via-white to-cyan-50/60 p-5 md:p-7">
      <div>
        <div>
          <p className="flex items-center gap-2 text-xs font-extrabold tracking-[0.14em] text-brand-700">
            <MessageSquareText aria-hidden="true" size={16} /> 원본 근거 기반 질문
          </p>
          <h2 className="mt-2 text-xl font-extrabold tracking-tight text-slate-950">
            이 Excel에 바로 질문하세요
          </h2>
          <p className="mt-2 text-sm leading-6 text-slate-600">
            Agent가 질문에 필요한 도구를 선택하고, 답변을 확인한 원본 시트와 셀을 함께
            보여줍니다.
          </p>
        </div>
      </div>

      <div className="mt-5">
        {!sourceAvailable && (
          <div className="mb-4 flex gap-2 rounded-2xl border border-amber-200 bg-amber-50 p-4 text-sm leading-6 text-amber-800">
            <TriangleAlert className="mt-0.5 shrink-0" size={17} />
            <div>
              <p className="font-extrabold">원본 파일 보관기간이 만료되었습니다.</p>
              <p className="mt-0.5 text-xs">
                저장된 분석 결과는 계속 볼 수 있지만, 원본 셀이 필요한 질문은 사용할 수
                없습니다.
              </p>
            </div>
          </div>
        )}
        <QuestionComposer
          disabled={!sourceAvailable}
          isPending={questions.isPending}
          onAsk={questions.ask}
          onValidationClear={questions.clearValidation}
          validationMessage={questions.validationMessage}
        />
      </div>

      {questions.pendingQuestion && (
        <div className="mt-4 rounded-2xl bg-white/80 p-4 text-sm font-semibold text-slate-500">
          “{questions.pendingQuestion}”의 원본 근거를 찾고 있습니다…
        </div>
      )}
      {questions.errorMessage && (
        <div
          className="mt-4 flex gap-2 rounded-2xl bg-red-50 p-4 text-sm text-red-700"
          role="alert"
        >
          <TriangleAlert className="mt-0.5 shrink-0" size={16} /> {questions.errorMessage}
        </div>
      )}
      {latestAnswer && (
        <div className="mt-5">
          <QuestionAnswerCard answer={latestAnswer} />
        </div>
      )}
      {previousAnswers.length > 0 && (
        <details className="group mt-3 rounded-2xl border border-slate-200 bg-white/70 p-3">
          <summary className="flex cursor-pointer list-none items-center justify-center gap-2 text-xs font-extrabold text-slate-600">
            이전 질문 {previousAnswers.length}개 보기
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
                key={`${answer.question}-${previousAnswers.length - index}`}
              />
            ))}
          </div>
        </details>
      )}
    </section>
  )
}

export default WorkbookQuestionSection
