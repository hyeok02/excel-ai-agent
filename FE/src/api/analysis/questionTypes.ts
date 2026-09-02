export type WorkbookQuestionStatus = 'answered' | 'limited' | 'insufficient_evidence'

export interface WorkbookQuestionEvidence {
  kind: string
  sheetName: string
  reference: string
  description: string
  value: unknown
  formula: string | null
  label: string
}

export interface WorkbookQuestionAnswer {
  question: string
  answer: string
  status: WorkbookQuestionStatus
  confidence: number
  selectedTools: string[]
  evidence: WorkbookQuestionEvidence[]
  limitations: string[]
}
