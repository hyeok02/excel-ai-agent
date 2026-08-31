import { MessageSquareText, Trash2, TriangleAlert } from 'lucide-react'

import QuestionAnswerCard from '@/components/analysis/result/questions/QuestionAnswerCard'
import QuestionComposer from '@/components/analysis/result/questions/QuestionComposer'
import { useWorkbookQuestions } from '@/hooks/analysis/useWorkbookQuestions'

const WorkbookQuestionSection = ({ analysisId }: { analysisId: string }) => {
  const questions = useWorkbookQuestions(analysisId)
  return (
    <section className="mt-6 overflow-hidden rounded-3xl border border-brand-200 bg-gradient-to-br from-brand-50 via-white to-cyan-50/60 p-5 md:p-7">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <p className="flex items-center gap-2 text-xs font-extrabold tracking-[0.14em] text-brand-700">
            <MessageSquareText aria-hidden="true" size={16} /> EVIDENCE-BASED EXCEL Q&A
          </p>
          <h2 className="mt-2 text-xl font-extrabold tracking-tight text-slate-950">
            이 Excel에 바로 질문하세요
          </h2>
          <p className="mt-2 text-sm leading-6 text-slate-600">
            Agent가 질문에 필요한 도구를 선택하고, 답변을 확인한 원본 시트와 셀을 함께 보여줍니다.
          </p>
        </div>
        {questions.answers.length > 0 && (
          <button
            className="inline-flex items-center gap-1.5 rounded-xl px-3 py-2 text-xs font-bold text-slate-500 hover:bg-white"
            onClick={questions.clear}
            type="button"
          >
            <Trash2 aria-hidden="true" size={14} /> 대화 지우기
          </button>
        )}
      </div>

      <div className="mt-5">
        <QuestionComposer isPending={questions.isPending} onAsk={questions.ask} />
      </div>

      {questions.pendingQuestion && (
        <div className="mt-4 rounded-2xl bg-white/80 p-4 text-sm font-semibold text-slate-500">
          “{questions.pendingQuestion}”의 원본 근거를 찾고 있습니다…
        </div>
      )}
      {questions.errorMessage && (
        <div className="mt-4 flex gap-2 rounded-2xl bg-red-50 p-4 text-sm text-red-700" role="alert">
          <TriangleAlert className="mt-0.5 shrink-0" size={16} /> {questions.errorMessage}
        </div>
      )}
      {questions.answers.length > 0 && (
        <div className="mt-5 space-y-3">
          {questions.answers.map((answer, index) => (
            <QuestionAnswerCard answer={answer} key={`${answer.question}-${index}`} />
          ))}
        </div>
      )}
    </section>
  )
}

export default WorkbookQuestionSection
