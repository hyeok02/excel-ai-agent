import { useEffect, useRef } from 'react'

import {
  askWorkbookQuestion,
  type InsightReportResult,
  type WorkbookQuestionAnswer,
  type WorkbookQuestionContext,
} from '@/api/analysis'
import { buildClarificationRequest } from '@/components/analysis/result/questions/questionClarification'
import { buildQuestionContext } from '@/components/analysis/result/questions/questionContext'
import { getQuestionValidationMessage } from '@/components/analysis/result/questions/questionValidation'
import { executeQuestionRequest } from '@/hooks/analysis/questionRequest'
import {
  canSubmitQuestion,
  type QuestionSession,
  reduceQuestionSession,
} from '@/hooks/analysis/questionSession'
import { getErrorMessage } from '@/utils/apiClient'

export const useQuestionSubmission = (
  session: QuestionSession,
  sourceAvailable: boolean,
  report: InsightReportResult | null,
  update: (action: Parameters<typeof reduceQuestionSession>[1]) => void,
) => {
  const { scope, analysisId } = session
  const pendingScope = useRef<object | null>(null)
  const active = useRef<{ scope: object; sourceAvailable: boolean } | null>(null)
  useEffect(() => {
    active.current = { scope, sourceAvailable }
    return () => {
      active.current = null
    }
  }, [scope, sourceAvailable])

  const submit = async (question: string, context?: WorkbookQuestionContext) => {
    if (
      !canSubmitQuestion(
        session,
        active.current?.scope,
        pendingScope.current,
        active.current?.sourceAvailable === true,
      )
    )
      return false
    const normalized = question.trim()
    const message = getQuestionValidationMessage(normalized)
    if (message) {
      update({ scope, type: 'validation', message })
      return false
    }
    pendingScope.current = scope
    update({ scope, type: 'start', question: normalized })
    return executeQuestionRequest({
      scope,
      request: () =>
        askWorkbookQuestion(
          analysisId,
          normalized,
          context ?? buildQuestionContext(session.answers, report),
        ),
      isActive: () => active.current?.scope === scope,
      update,
      errorMessage: getErrorMessage,
      release: () => {
        if (pendingScope.current === scope) pendingScope.current = null
      },
    })
  }

  return {
    ask: (question: string) => submit(question),
    choose: (answer: WorkbookQuestionAnswer, optionId: string) => {
      const request = buildClarificationRequest(session.answers, answer, optionId, report)
      return request ? submit(request.question, request.context) : Promise.resolve(false)
    },
  }
}
