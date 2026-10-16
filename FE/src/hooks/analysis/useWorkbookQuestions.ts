import { useEffect, useRef, useState } from 'react'

import {
  askWorkbookQuestion,
  getWorkbookQuestionHistory,
  type InsightReportResult,
} from '@/api/analysis'
import { useAuth } from '@/app/providers/auth-context'
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
  const { user } = useAuth()
  const ownerId = user?.id ?? null
  const [session, setSession] = useState(() => createQuestionSession(analysisId, ownerId))
  const [restoreAttempt, setRestoreAttempt] = useState(0)
  const pendingScope = useRef<object | null>(null)
  const earlierScope = useRef<object | null>(null)
  if (session.analysisId !== analysisId || session.ownerId !== ownerId) {
    setSession(createQuestionSession(analysisId, ownerId))
  }
  const { scope } = session
  const update = (action: Parameters<typeof reduceQuestionSession>[1]) =>
    setSession((state) => reduceQuestionSession(state, action))

  useEffect(() => {
    if (!ownerId) return
    const controller = new AbortController()
    void getWorkbookQuestionHistory(analysisId, null, controller.signal)
      .then((page) => {
        if (controller.signal.aborted) return
        setSession((state) =>
          reduceQuestionSession(state, { scope, type: 'restoreSuccess', page }),
        )
      })
      .catch((error: unknown) => {
        if (controller.signal.aborted) return
        setSession((state) =>
          reduceQuestionSession(state, {
            scope,
            type: 'restoreError',
            message: getErrorMessage(error),
          }),
        )
      })
    return () => controller.abort()
  }, [analysisId, ownerId, scope, restoreAttempt])

  const retryHistory = () => {
    if (session.historyStatus !== 'error') return
    update({ scope, type: 'restoreStart' })
    setRestoreAttempt((attempt) => attempt + 1)
  }

  const loadEarlier = async () => {
    const before = session.nextCursor
    if (!before || session.historyStatus !== 'ready' || earlierScope.current === scope) {
      return
    }
    earlierScope.current = scope
    update({ scope, type: 'earlierStart' })
    try {
      const page = await getWorkbookQuestionHistory(analysisId, before)
      update({ scope, type: 'earlierSuccess', before, page })
    } catch (error) {
      update({ scope, type: 'earlierError', message: getErrorMessage(error) })
    } finally {
      if (earlierScope.current === scope) earlierScope.current = null
      update({ scope, type: 'earlierSettled' })
    }
  }

  const ask = async (question: string) => {
    const normalized = question.trim()
    if (
      !ownerId ||
      pendingScope.current === scope ||
      session.analysisId !== analysisId ||
      session.ownerId !== ownerId ||
      session.historyStatus !== 'ready'
    ) {
      return false
    }
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
    historyReady: session.historyStatus === 'ready',
    isRestoring: session.historyStatus === 'loading',
    historyErrorMessage: session.historyErrorMessage,
    retryHistory,
    hasEarlierHistory: session.nextCursor !== null,
    isLoadingEarlier: session.loadingEarlier,
    earlierHistoryErrorMessage: session.earlierHistoryErrorMessage,
    loadEarlier,
    isPending: session.pendingQuestion !== null,
    pendingQuestion: session.pendingQuestion,
    validationMessage: session.validationMessage,
  }
}
