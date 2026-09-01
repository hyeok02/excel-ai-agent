import { useMutation } from '@tanstack/react-query'
import { useState } from 'react'

import { askWorkbookQuestion, type WorkbookQuestionAnswer } from '@/api/analysis'
import { getQuestionValidationMessage } from '@/components/analysis/result/questions/questionValidation'
import { getErrorMessage } from '@/utils/apiClient'

export const useWorkbookQuestions = (analysisId: string) => {
  const [answers, setAnswers] = useState<WorkbookQuestionAnswer[]>([])
  const [pendingQuestion, setPendingQuestion] = useState<string | null>(null)
  const [validationMessage, setValidationMessage] = useState<string | null>(null)

  const questionMutation = useMutation({
    mutationFn: (question: string) => askWorkbookQuestion(analysisId, question),
    onSuccess: (answer) => setAnswers((items) => [...items, answer]),
    onSettled: () => setPendingQuestion(null),
  })

  const ask = (question: string) => {
    const normalized = question.trim()
    if (questionMutation.isPending) return false
    const message = getQuestionValidationMessage(normalized)
    if (message) {
      setValidationMessage(message)
      return false
    }
    setValidationMessage(null)
    questionMutation.reset()
    setPendingQuestion(normalized)
    questionMutation.mutate(normalized)
    return true
  }

  return {
    answers,
    ask,
    clearValidation: () => setValidationMessage(null),
    errorMessage: questionMutation.isError
      ? getErrorMessage(questionMutation.error)
      : null,
    isPending: questionMutation.isPending,
    pendingQuestion,
    validationMessage,
  }
}
