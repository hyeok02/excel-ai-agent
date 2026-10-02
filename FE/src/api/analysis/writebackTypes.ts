export type WritebackStatus = 'PROPOSED' | 'BLOCKED' | 'APPLIED' | 'REJECTED' | 'FAILED'

/** 수식으로 이어져 있지 않아 함께 확인해야 하는 셀. */
export interface WritebackRelatedCell {
  sheetName: string
  reference: string
  currentValue: string | number | boolean | null
  suggestedValue: string | number | boolean | null
  kind: 'total' | 'mirror'
  reason: string
  /** 합계 셀일 때만 채워진다. [바꾸기 전 식, 바꾼 뒤 식] */
  breakdown?: string[]
  parts?: string[]
}

export interface WritebackChange {
  sheetName: string
  reference: string
  oldValue: string | number | boolean | null
  newValue: string | number | boolean | null
  reason: string
  changeType?: 'value' | 'clear' | 'formula'
  valueType?: 'text' | 'number' | 'boolean' | 'date' | 'datetime' | 'blank' | 'formula'
  affectedCells?: string[]
  riskLevel?: 'low' | 'medium' | 'high'
  contextCells?: Array<{
    reference: string
    value: string | number | boolean | null
  }>
  relatedCells?: WritebackRelatedCell[]
  /** 새 값이 요청에 없고 계산으로 나온 경우, 그 계산 과정. */
  derivation?: string | null
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
  /** 이 수정이 올라탄 직전 수정본. 원본에서 바로 시작했으면 없다. */
  baseWritebackId?: string | null
}
