import type { AnalysisProvenance } from '@/api/analysis/evidenceTypes'

export type FormulaRiskKind =
  | 'broken_reference'
  | 'missing_sheet'
  | 'external_reference'
  | 'dynamic_function'
  | 'formula_pattern_mismatch'
  | 'hardcoded_value'

export type FormulaRiskSeverity = 'error' | 'warning'
export type FormulaRiskLevel = 'low' | 'medium' | 'high' | 'critical'

export interface FormulaRiskImpactResult {
  affectedFormulaCount: number
  affectedSheetCount: number
  affectedSheets: string[]
  maxDepth: number
  riskScore: number
  riskLevel: FormulaRiskLevel
}

export interface FormulaRiskFindingResult {
  kind: FormulaRiskKind
  severity: FormulaRiskSeverity
  sheetName: string
  cell: string
  message: string
  formula: string
  reference: string | null
  functionName: string | null
  observedValue?: string | number | boolean | null
  provenance?: AnalysisProvenance | null
  impact?: FormulaRiskImpactResult | null
}

export interface FormulaRiskSummaryResult {
  totalCount: number
  errorCount: number
  warningCount: number
  brokenReferenceCount: number
  missingSheetCount: number
  externalReferenceCount: number
  dynamicFunctionCount: number
  patternMismatchCount: number
  hardcodedValueCount: number
  highRiskCount: number
  criticalRiskCount: number
  findings: FormulaRiskFindingResult[]
}
