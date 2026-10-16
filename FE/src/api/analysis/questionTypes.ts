export type WorkbookQuestionStatus = 'answered' | 'limited' | 'insufficient_evidence'

export interface WorkbookQuestionVerification {
  level: 'unverified' | 'source_checked' | 'request_checked'
  checks: string[]
}

export interface WorkbookQuestionEvidence {
  kind: string
  sheetName: string
  reference: string
  description: string
  value: unknown
  formula: string | null
  label: string
  numberFormat?: string | null
}

export interface WorkbookQuestionAnswer {
  question: string
  resolvedQuestion?: string | null
  answer: string
  status: WorkbookQuestionStatus
  confidence: number
  selectedTools: string[]
  evidence: WorkbookQuestionEvidence[]
  limitations: string[]
  verification?: WorkbookQuestionVerification
}

export interface WorkbookQuestionHistoryItem {
  id: string
  createdAt: string
  answer: WorkbookQuestionAnswer
}

/** Each page is chronological; nextCursor retrieves the preceding, older page. */
export interface WorkbookQuestionHistoryPage {
  items: WorkbookQuestionHistoryItem[]
  nextCursor: string | null
}

export interface WorkbookQuestionContext {
  turns: { question: string; evidence: string[]; needs_clarification?: boolean }[]
  insights: { title: string; topic: string | null; evidence: string[] }[]
}
