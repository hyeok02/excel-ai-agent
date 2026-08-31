import { useMutation } from '@tanstack/react-query'
import { useState } from 'react'

import { askWorkbookQuestion, type WorkbookQuestionAnswer } from '@/api/analysis'
import { getErrorMessage } from '@/utils/apiClient'

export const useWorkbookQuestions = (analysisId: string) => {
  const [answers, setAnswers] = useState<WorkbookQuestionAnswer[]>([])
  const [pendingQuestion, setPendingQuestion] = useState<string | null>(null)

  const questionMutation = useMutation({
    mutationFn: (question: string) => askWorkbookQuestion(analysisId, question),
    onSuccess: (answer) => setAnswers((items) => [...items, answer]),
    onSettled: () => setPendingQuestion(null),
  })

  const ask = (question: string) => {
    const normalized = question.trim()
    if (normalized.length < 2 || questionMutation.isPending) return false
    questionMutation.reset()
    setPendingQuestion(normalized)
    questionMutation.mutate(normalized)
    return true
  }

  const clear = () => {
    setAnswers([])
    questionMutation.reset()
  }

  return {
    answers,
    ask,
    clear,
    errorMessage: questionMutation.isError
      ? getErrorMessage(questionMutation.error)
      : null,
    isPending: questionMutation.isPending,
    pendingQuestion,
  }
}
