import type { InsightReportResult } from '@/api/analysis/insightTypes'
import type {
  WorkbookQuestionAnswer,
  WorkbookQuestionContext,
} from '@/api/analysis/questionTypes'

import { prepareInsightReportPresentation } from '../insightReportPresentation.ts'

const MAX_ITEMS = 6
const MAX_REFERENCES = 12
const CELL_RANGE = /^[A-Z]{1,3}[1-9]\d*(?::[A-Z]{1,3}[1-9]\d*)?$/i

const boundedText = (text: string | null | undefined, limit: number) => {
  const value = text?.trim() ?? ''
  return value && value.length <= limit ? value : null
}

const qualifiedReference = (sheetName: string, address: string) => {
  const cell = address.trim().replaceAll('$', '').toUpperCase()
  if (!sheetName || !CELL_RANGE.test(cell)) return null
  const reference = `'${sheetName.replaceAll("'", "''")}'!${cell}`
  return reference.length <= 200 ? reference : null
}

const insightReference = (reference: string) => {
  const separator = reference.lastIndexOf('!')
  if (separator < 1) return null
  const sheet = reference.slice(0, separator).trim()
  const unquoted =
    sheet.startsWith("'") && sheet.endsWith("'")
      ? sheet.slice(1, -1).replaceAll("''", "'")
      : sheet
  return qualifiedReference(unquoted, reference.slice(separator + 1))
}

const uniqueReferences = (references: (string | null)[]) =>
  [...new Set(references.filter((reference) => reference !== null))].slice(
    0,
    MAX_REFERENCES,
  )

/** Context is a referent hint only. Answer prose, values and insight facts never travel. */
export const buildQuestionContext = (
  answers: WorkbookQuestionAnswer[],
  report: InsightReportResult | null,
): WorkbookQuestionContext => {
  const turns = answers
    .flatMap((answer) => {
      const question =
        boundedText(answer.resolvedQuestion, 1000) ?? boundedText(answer.question, 1000)
      return question
        ? [
            {
              question,
              evidence: uniqueReferences(
                answer.evidence.map((item) =>
                  qualifiedReference(item.sheetName, item.reference),
                ),
              ),
            },
          ]
        : []
    })
    .slice(-MAX_ITEMS)
  const visible = report ? prepareInsightReportPresentation(report).report.insights : []
  const insights = visible
    .flatMap((insight) => {
      const title = boundedText(insight.title, 200)
      const evidence = uniqueReferences(insight.evidence.map(insightReference))
      return title && evidence.length
        ? [{ title, topic: boundedText(insight.topic, 200), evidence }]
        : []
    })
    .slice(0, MAX_ITEMS)
  return { turns, insights }
}

export const resolvedQuestionLabel = (answer: WorkbookQuestionAnswer) => {
  const resolved = boundedText(answer.resolvedQuestion, 1000)
  return resolved && resolved !== answer.question.trim() ? resolved : null
}
