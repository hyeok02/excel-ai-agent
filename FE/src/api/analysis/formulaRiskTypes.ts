import type { AnalysisProvenance } from '@/api/analysis/evidenceTypes'

export type FormulaRiskKind =
  | 'broken_reference'
  | 'missing_sheet'
  | 'external_reference'
  | 'dynamic_function'

export type FormulaRiskSeverity = 'error' | 'warning'

export interface FormulaRiskFindingResult {
  kind: FormulaRiskKind
  severity: FormulaRiskSeverity
  sheetName: string
  cell: string
  message: string
  formula: string
  reference: string | null
  functionName: string | null
  provenance?: AnalysisProvenance | null
}

export interface FormulaRiskSummaryResult {
  totalCount: number
  errorCount: number
  warningCount: number
  brokenReferenceCount: number
  missingSheetCount: number
  externalReferenceCount: number
  dynamicFunctionCount: number
  findings: FormulaRiskFindingResult[]
}
