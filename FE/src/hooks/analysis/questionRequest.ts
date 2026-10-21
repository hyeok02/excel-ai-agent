import type { WorkbookQuestionAnswer } from '../../api/analysis/questionTypes.ts'
import type { reduceQuestionSession } from './questionSession.ts'

interface QuestionRequest {
  scope: object
  request: () => Promise<WorkbookQuestionAnswer>
  isActive: () => boolean
  update: (action: Parameters<typeof reduceQuestionSession>[1]) => void
  errorMessage: (error: unknown) => string
  release: () => void
}

/** A completed request must not clear a draft belonging to another mounted session. */
export const executeQuestionRequest = async ({
  scope,
  request,
  isActive,
  update,
  errorMessage,
  release,
}: QuestionRequest): Promise<boolean> => {
  try {
    const answer = await request()
    if (!isActive()) return false
    update({ scope, type: 'success', answer })
    return true
  } catch (error) {
    if (isActive()) update({ scope, type: 'error', message: errorMessage(error) })
    return false
  } finally {
    release()
    if (isActive()) update({ scope, type: 'settled' })
  }
}
