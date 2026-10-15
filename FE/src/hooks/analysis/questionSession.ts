import type { WorkbookQuestionAnswer } from '@/api/analysis/questionTypes'

export interface QuestionSession {
  analysisId: string
  scope: object
  answers: WorkbookQuestionAnswer[]
  pendingQuestion: string | null
  validationMessage: string | null
  errorMessage: string | null
}

type SessionAction = { scope: object } & (
  | { type: 'start'; question: string }
  | { type: 'success'; answer: WorkbookQuestionAnswer }
  | { type: 'error'; message: string }
  | { type: 'settled' }
  | { type: 'validation'; message: string | null }
)

export const createQuestionSession = (analysisId: string): QuestionSession => ({
  analysisId,
  scope: {},
  answers: [],
  pendingQuestion: null,
  validationMessage: null,
  errorMessage: null,
})

/** Ignore every completion from a previous analysis, including A -> B -> A navigation. */
export const reduceQuestionSession = (
  state: QuestionSession,
  action: SessionAction,
): QuestionSession => {
  if (action.scope !== state.scope) return state
  switch (action.type) {
    case 'start':
      return {
        ...state,
        pendingQuestion: action.question,
        validationMessage: null,
        errorMessage: null,
      }
    case 'success':
      return { ...state, answers: [...state.answers, action.answer] }
    case 'error':
      return { ...state, errorMessage: action.message }
    case 'settled':
      return { ...state, pendingQuestion: null }
    case 'validation':
      return { ...state, validationMessage: action.message }
  }
}
