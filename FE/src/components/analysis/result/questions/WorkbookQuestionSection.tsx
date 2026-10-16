import { MessageSquareText, TriangleAlert } from 'lucide-react'

import type { InsightReportResult } from '@/api/analysis'
import QuestionAnswerCard from '@/components/analysis/result/questions/QuestionAnswerCard'
import QuestionComposer from '@/components/analysis/result/questions/QuestionComposer'
import QuestionHistoryNotice from '@/components/analysis/result/questions/QuestionHistoryNotice'
import QuestionHistoryPanel from '@/components/analysis/result/questions/QuestionHistoryPanel'
import { useWorkbookQuestions } from '@/hooks/analysis/useWorkbookQuestions'

interface WorkbookQuestionSectionProps {
  analysisId: string
  sourceAvailable: boolean
  suggestions: string[]
  insightReport?: InsightReportResult | null
}

const WorkbookQuestionSection = ({
  analysisId,
  sourceAvailable,
  suggestions,
  insightReport = null,
}: WorkbookQuestionSectionProps) => {
  const questions = useWorkbookQuestions(analysisId, insightReport)
  const latestAnswer = questions.answers.at(-1)
  return (
    <section
      aria-labelledby="workbook-question-heading"
      className="mt-6 overflow-hidden rounded-3xl border border-brand-200 bg-gradient-to-br from-brand-50 via-white to-cyan-50/60 p-5 md:p-7"
    >
      <div>
        <div>
          <p className="flex items-center gap-2 text-xs font-extrabold tracking-[0.14em] text-brand-700">
            <MessageSquareText aria-hidden="true" size={16} /> 원본 근거 기반 질문
          </p>
          <h2
            className="mt-2 text-xl font-extrabold tracking-tight text-slate-950"
            id="workbook-question-heading"
          >
            이 Excel에 바로 질문하세요
          </h2>
          <p className="mt-2 text-sm leading-6 text-slate-600">
            Agent가 질문에 필요한 도구를 선택하고, 답변을 확인한 원본 시트와 셀을 함께
            보여줍니다. 이 분석의 인사이트와 앞선 질문을 이어서 물어볼 수 있습니다.
          </p>
          <p className="mt-1 text-xs leading-5 text-slate-500">
            질문과 답변은 이 분석에 자동 저장되어 다시 방문해도 이어집니다. 저장된 근거와
            검증 표시는 답변 당시의 내용입니다.
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
                저장된 분석 결과와 이전 대화는 계속 볼 수 있지만, 원본 셀이 필요한 새
                질문은 사용할 수 없습니다.
              </p>
            </div>
          </div>
        )}
        <QuestionHistoryNotice
          errorMessage={questions.historyErrorMessage}
          isLoading={questions.isRestoring}
          onRetry={questions.retryHistory}
        />
        <QuestionComposer
          disabled={!sourceAvailable || !questions.historyReady}
          disabledMessage={
            !sourceAvailable
              ? '원본 파일 보관기간이 지나 질문할 수 없습니다.'
              : '이전 대화를 불러온 뒤 질문할 수 있습니다.'
          }
          isPending={questions.isPending}
          onAsk={questions.ask}
          suggestions={suggestions}
          onValidationClear={questions.clearValidation}
          validationMessage={questions.validationMessage}
        />
      </div>

      {questions.pendingQuestion && (
        <div
          aria-atomic="true"
          aria-live="polite"
          className="mt-4 rounded-2xl bg-white/80 p-4 text-sm text-slate-500"
          role="status"
        >
          <p className="font-extrabold text-slate-700">답변 준비 중</p>
          <p className="mt-1">
            “{questions.pendingQuestion}”에 필요한 원본을 확인하고 있습니다.
          </p>
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
      <QuestionHistoryPanel
        answers={questions.answers}
        errorMessage={questions.earlierHistoryErrorMessage}
        hasEarlier={questions.hasEarlierHistory}
        isLoading={questions.isLoadingEarlier}
        onLoadEarlier={questions.loadEarlier}
      />
    </section>
  )
}

export default WorkbookQuestionSection
