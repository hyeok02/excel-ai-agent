import { useRef, useState } from 'react'

import { askWorkbookQuestion, type InsightReportResult } from '@/api/analysis'
import { buildQuestionContext } from '@/components/analysis/result/questions/questionContext'
import { getQuestionValidationMessage } from '@/components/analysis/result/questions/questionValidation'
import {
  createQuestionSession,
  reduceQuestionSession,
} from '@/hooks/analysis/questionSession'
import { getErrorMessage } from '@/utils/apiClient'

export const useWorkbookQuestions = (
  analysisId: string,
  report: InsightReportResult | null = null,
) => {
  const [session, setSession] = useState(() => createQuestionSession(analysisId))
  const pendingScope = useRef<object | null>(null)
  if (session.analysisId !== analysisId) {
    setSession(createQuestionSession(analysisId))
  }
  const update = (action: Parameters<typeof reduceQuestionSession>[1]) =>
    setSession((state) => reduceQuestionSession(state, action))

  const ask = async (question: string) => {
    const normalized = question.trim()
    const scope = session.scope
    if (pendingScope.current === scope || session.analysisId !== analysisId) return false
    const message = getQuestionValidationMessage(normalized)
    if (message) {
      update({ scope, type: 'validation', message })
      return false
    }
    pendingScope.current = scope
    update({ scope, type: 'start', question: normalized })
    try {
      const context = buildQuestionContext(session.answers, report)
      const answer = await askWorkbookQuestion(analysisId, normalized, context)
      update({ scope, type: 'success', answer })
      return true
    } catch (error) {
      update({ scope, type: 'error', message: getErrorMessage(error) })
      return false
    } finally {
      if (pendingScope.current === scope) pendingScope.current = null
      update({ scope, type: 'settled' })
    }
  }

  return {
    answers: session.answers,
    ask,
    clearValidation: () =>
      update({ scope: session.scope, type: 'validation', message: null }),
    errorMessage: session.errorMessage,
    isPending: session.pendingQuestion !== null,
    pendingQuestion: session.pendingQuestion,
    validationMessage: session.validationMessage,
  }
}
