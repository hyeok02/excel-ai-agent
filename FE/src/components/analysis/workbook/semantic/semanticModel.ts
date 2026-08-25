import type { AnalysisInclusion, SemanticReason } from '@/api/analysis'

export const SEMANTIC_SHEET_ROLES = [
  'input',
  'calculation',
  'output',
  'documentation',
  'system',
] as const

export type SemanticSheetRole = (typeof SEMANTIC_SHEET_ROLES)[number]

export const SEMANTIC_SHEET_IMPORTANCE_LEVELS = [
  'low',
  'medium',
  'high',
  'critical',
] as const

export type SemanticSheetImportance = (typeof SEMANTIC_SHEET_IMPORTANCE_LEVELS)[number]

export interface SheetSemanticClassification {
  role: SemanticSheetRole
  importance: SemanticSheetImportance
  confidence: number
  importanceScore: number
  reasons: SemanticReason[]
}

interface SheetSemanticCarrier {
  analysisInclusion?: AnalysisInclusion | null
  sheetClassification?: unknown
}

const isRecord = (value: unknown): value is Record<string, unknown> =>
  typeof value === 'object' && value !== null

const isSheetRole = (value: unknown): value is SemanticSheetRole =>
  typeof value === 'string' && SEMANTIC_SHEET_ROLES.includes(value as SemanticSheetRole)

const isSheetImportance = (value: unknown): value is SemanticSheetImportance =>
  typeof value === 'string' &&
  SEMANTIC_SHEET_IMPORTANCE_LEVELS.includes(value as SemanticSheetImportance)

const normalizeSheetClassification = (
  value: unknown,
): SheetSemanticClassification | null => {
  if (
    !isRecord(value) ||
    !isSheetRole(value.role) ||
    !isSheetImportance(value.importance)
  ) {
    return null
  }

  return {
    role: value.role,
    importance: value.importance,
    confidence: typeof value.confidence === 'number' ? value.confidence : 0,
    importanceScore:
      typeof value.importanceScore === 'number' ? value.importanceScore : 0,
    reasons: Array.isArray(value.reasons) ? (value.reasons as SemanticReason[]) : [],
  }
}

export const getSheetSemanticMetadata = (sheet: unknown) => {
  if (!isRecord(sheet)) {
    return { analysisInclusion: null, classification: null }
  }

  const carrier = sheet as SheetSemanticCarrier
  return {
    analysisInclusion: carrier.analysisInclusion ?? null,
    classification: normalizeSheetClassification(carrier.sheetClassification),
  }
}
