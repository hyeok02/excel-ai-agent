import type {
  WorkbookQuestionAnswer,
  WorkbookQuestionHistoryPage,
} from '@/api/analysis/questionTypes'

export interface QuestionSession {
  analysisId: string
  ownerId: string | null
  scope: object
  answers: WorkbookQuestionAnswer[]
  pendingQuestion: string | null
  validationMessage: string | null
  errorMessage: string | null
  historyStatus: 'loading' | 'ready' | 'error'
  historyErrorMessage: string | null
  nextCursor: string | null
  loadingEarlier: boolean
  earlierHistoryErrorMessage: string | null
}

type SessionAction = { scope: object } & (
  | { type: 'start'; question: string }
  | { type: 'success'; answer: WorkbookQuestionAnswer }
  | { type: 'error'; message: string }
  | { type: 'settled' }
  | { type: 'validation'; message: string | null }
  | { type: 'restoreStart' }
  | { type: 'restoreSuccess'; page: WorkbookQuestionHistoryPage }
  | { type: 'restoreError'; message: string }
  | { type: 'earlierStart' }
  | { type: 'earlierSuccess'; before: string; page: WorkbookQuestionHistoryPage }
  | { type: 'earlierError'; message: string }
  | { type: 'earlierSettled' }
)

export const createQuestionSession = (
  analysisId: string,
  ownerId: string | null = null,
): QuestionSession => ({
  analysisId,
  ownerId,
  scope: {},
  answers: [],
  pendingQuestion: null,
  validationMessage: null,
  errorMessage: null,
  historyStatus: 'loading',
  historyErrorMessage: null,
  nextCursor: null,
  loadingEarlier: false,
  earlierHistoryErrorMessage: null,
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
    case 'restoreStart':
      return { ...state, historyStatus: 'loading', historyErrorMessage: null }
    case 'restoreSuccess':
      return {
        ...state,
        answers: action.page.items.map((item) => item.answer),
        historyStatus: 'ready',
        historyErrorMessage: null,
        nextCursor: action.page.nextCursor,
      }
    case 'restoreError':
      return { ...state, historyStatus: 'error', historyErrorMessage: action.message }
    case 'earlierStart':
      return { ...state, loadingEarlier: true, earlierHistoryErrorMessage: null }
    case 'earlierSuccess':
      // A completed cursor is never appended twice; new answers stay at the end.
      if (action.before !== state.nextCursor) return state
      return {
        ...state,
        answers: [...action.page.items.map((item) => item.answer), ...state.answers],
        nextCursor: action.page.nextCursor,
        earlierHistoryErrorMessage: null,
      }
    case 'earlierError':
      return { ...state, earlierHistoryErrorMessage: action.message }
    case 'earlierSettled':
      return { ...state, loadingEarlier: false }
  }
}
