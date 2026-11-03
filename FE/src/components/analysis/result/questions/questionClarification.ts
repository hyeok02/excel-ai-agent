import type { InsightReportResult } from '@/api/analysis/insightTypes'
import type {
  WorkbookQuestionAnswer,
  WorkbookQuestionClarificationOption,
} from '@/api/analysis/questionTypes'

import { buildQuestionContext } from './questionContext.ts'

const bounded = (value: unknown, min: number, max: number): value is string =>
  typeof value === 'string' && value.trim().length >= min && value.length <= max

/** Only structured server options become actions; answer prose is never executable. */
export const getClarificationOptions = (
  answer: WorkbookQuestionAnswer,
): WorkbookQuestionClarificationOption[] => {
  const options = answer.clarificationOptions
  if (answer.status !== 'insufficient_evidence' || !Array.isArray(options)) return []
  if (options.length > 6) return []
  const seen = new Set<string>()
  return options.filter((option) => {
    if (
      !option ||
      !bounded(option.id, 64, 64) ||
      !/^[0-9a-f]{64}$/.test(option.id) ||
      !bounded(option.label, 1, 200) ||
      !bounded(option.scope, 0, 200) ||
      !bounded(option.details, 0, 1000) ||
      !bounded(option.question, 2, 1000) ||
      seen.has(option.id)
    )
      return false
    seen.add(option.id)
    return true
  })
}

export const buildClarificationRequest = (
  answers: WorkbookQuestionAnswer[],
  answer: WorkbookQuestionAnswer,
  optionId: string,
  report: InsightReportResult | null,
) => {
  const requestedSource = answer.resolvedQuestion || answer.question
  const requestedOption = getClarificationOptions(answer).find(
    (item) => item.id === optionId,
  )
  if (!requestedOption || !bounded(requestedSource, 2, 1000)) return null

  // Restored answers are deserialized into new objects, so reference equality is
  // not a stable authorization boundary. Rebind the click to the canonical
  // answer currently stored in the session, while still requiring the complete
  // server-issued option payload to match before it can become a request.
  const canonicalAnswer = answers.find((candidate) => {
    const source = candidate.resolvedQuestion || candidate.question
    if (source !== requestedSource) return false
    const option = getClarificationOptions(candidate).find((item) => item.id === optionId)
    return (
      option?.label === requestedOption.label &&
      option.scope === requestedOption.scope &&
      option.details === requestedOption.details &&
      option.question === requestedOption.question
    )
  })
  if (!canonicalAnswer) return null

  const option = getClarificationOptions(canonicalAnswer).find(
    (item) => item.id === optionId,
  )
  const source = canonicalAnswer.resolvedQuestion || canonicalAnswer.question
  if (!option || !bounded(source, 2, 1000)) return null
  return {
    question: option.question,
    context: {
      ...buildQuestionContext(answers, report),
      selection: { source_question: source, option_id: option.id },
    },
  }
}
