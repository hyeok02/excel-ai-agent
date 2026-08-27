import type { AnalysisProvenance } from '@/api/analysis/evidenceTypes'

export const SEMANTIC_ROLES = [
  'title',
  'description',
  'unit',
  'header',
  'data',
  'formula',
  'note',
  'total',
  'input',
  'calculation',
  'output',
  'instruction',
  'warning',
  'source_note',
  'rule_note',
  'system_cache',
  'ignore',
  'unknown',
] as const

export type SemanticRole = (typeof SEMANTIC_ROLES)[number]

export interface SemanticReason {
  code: string
  message: string
  evidenceCells: string[]
}

export interface SemanticClassification {
  role: SemanticRole
  confidence: number
  reasons: SemanticReason[]
  provenance?: AnalysisProvenance | null
}

export const ANALYSIS_DECISIONS = ['include', 'exclude'] as const
export type AnalysisDecision = (typeof ANALYSIS_DECISIONS)[number]

export interface AnalysisInclusion {
  decision: AnalysisDecision
  reasonCode: string
  reason: string
  provenance?: AnalysisProvenance | null
}

export const SHEET_ROLES = [
  'input',
  'calculation',
  'output',
  'documentation',
  'system',
] as const
export type SheetRole = (typeof SHEET_ROLES)[number]

export const SHEET_IMPORTANCE_LEVELS = ['low', 'medium', 'high', 'critical'] as const
export type SheetImportance = (typeof SHEET_IMPORTANCE_LEVELS)[number]

export interface SheetRoleReason {
  code: string
  message: string
  evidenceCells: string[]
}

export interface SheetClassification {
  role: SheetRole
  importance: SheetImportance
  confidence: number
  importanceScore: number
  reasons: SheetRoleReason[]
  provenance?: AnalysisProvenance | null
}
