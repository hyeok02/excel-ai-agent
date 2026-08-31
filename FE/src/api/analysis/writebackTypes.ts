export type WritebackStatus =
  | 'PROPOSED'
  | 'BLOCKED'
  | 'APPLIED'
  | 'REJECTED'
  | 'FAILED'

export interface WritebackChange {
  sheetName: string
  reference: string
  oldValue: string | number | boolean | null
  newValue: string | number | boolean
  reason: string
}

export interface WritebackProposal {
  instruction: string
  status: 'ready' | 'blocked'
  summary: string
  changes: WritebackChange[]
  risks: string[]
  limitations: string[]
}

export interface WritebackVerificationCheck {
  name: string
  passed: boolean
  detail: string
}

export interface WritebackVerification {
  changedCells: string[]
  checks: WritebackVerificationCheck[]
  verified: boolean
}

export interface WorkbookWriteback {
  writebackId: string
  analysisId: string
  status: WritebackStatus
  instruction: string
  proposal: WritebackProposal
  verification: WritebackVerification | null
  requestedBy: string
  approvedBy: string | null
  createdAt: string
  updatedAt: string
  downloadable: boolean
}
