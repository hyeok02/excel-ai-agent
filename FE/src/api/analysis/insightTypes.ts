export type InsightCategory = 'summary' | 'structure' | 'formula' | 'risk'
export type InsightSeverity = 'info' | 'warning' | 'critical'
export type InsightValidationStatus = 'verified' | 'limited'

export interface InsightValidationSummary {
  generatedCount: number
  verifiedCount: number
  limitedCount: number
  blockedCount: number
  notices: string[]
}

export interface InsightResult {
  title: string
  fact: string
  cause: string | null
  impact: string
  category: InsightCategory
  severity: InsightSeverity
  evidence: string[]
  recommendation: string | null
  confidence: number | null
  isIncomplete: boolean
  validationStatus: InsightValidationStatus | null
  validationReasons: string[]
}

export interface InsightReportResult {
  overview: string
  insights: InsightResult[]
  limitations: string[]
  hasIncompleteData: boolean
  validation: InsightValidationSummary | null
}

type UnknownRecord = Record<string, unknown>

const isRecord = (value: unknown): value is UnknownRecord =>
  typeof value === 'object' && value !== null && !Array.isArray(value)

const readText = (value: unknown) =>
  typeof value === 'string' && value.trim() ? value.trim() : null

const readTextList = (value: unknown) =>
  Array.isArray(value)
    ? value.map(readText).filter((item): item is string => item !== null)
    : []

const readCategory = (value: unknown): InsightCategory =>
  value === 'structure' || value === 'formula' || value === 'risk' ? value : 'summary'

const readSeverity = (value: unknown): InsightSeverity =>
  value === 'warning' || value === 'critical' ? value : 'info'

const readConfidence = (value: unknown) => {
  if (typeof value !== 'number' || !Number.isFinite(value)) return null
  return Math.min(1, Math.max(0, value))
}

const readValidationStatus = (value: unknown): InsightValidationStatus | null =>
  value === 'verified' || value === 'limited' ? value : null

const readCount = (value: unknown) =>
  typeof value === 'number' && Number.isFinite(value) && value >= 0
    ? Math.floor(value)
    : 0

const normalizeValidation = (value: unknown): InsightValidationSummary | null => {
  if (!isRecord(value)) return null
  return {
    generatedCount: readCount(value.generatedCount),
    verifiedCount: readCount(value.verifiedCount),
    limitedCount: readCount(value.limitedCount),
    blockedCount: readCount(value.blockedCount),
    notices: readTextList(value.notices),
  }
}

const normalizeInsight = (value: unknown, index: number): InsightResult => {
  const insight = isRecord(value) ? value : {}
  const fact = readText(insight.fact) ?? readText(insight.description) ?? ''
  const impact = readText(insight.impact) ?? ''

  return {
    title: readText(insight.title) ?? `인사이트 ${index + 1}`,
    fact,
    cause: readText(insight.cause),
    impact,
    category: readCategory(insight.category),
    severity: readSeverity(insight.severity),
    evidence: readTextList(insight.evidence),
    recommendation: readText(insight.recommendation),
    confidence: readConfidence(insight.confidence),
    isIncomplete: !fact || !impact,
    validationStatus: readValidationStatus(insight.validationStatus),
    validationReasons: readTextList(insight.validationReasons),
  }
}

export const normalizeInsightReport = (value: unknown): InsightReportResult | null => {
  if (!isRecord(value)) return null

  const insights = Array.isArray(value.insights)
    ? value.insights.map(normalizeInsight)
    : []

  return {
    overview: readText(value.overview) ?? 'Excel 분석 결과를 확인하세요.',
    insights,
    limitations: readTextList(value.limitations),
    hasIncompleteData: insights.some((insight) => insight.isIncomplete),
    validation: normalizeValidation(value.validation),
  }
}
