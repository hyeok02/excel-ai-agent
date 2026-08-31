export type InsightCategory = 'summary' | 'structure' | 'formula' | 'risk'
export type InsightSeverity = 'info' | 'warning' | 'critical'

export interface InsightResult {
  title: string
  fact: string
  cause: string | null
  impact: string
  category: InsightCategory
  severity: InsightSeverity
  evidence: string[]
  recommendation: string | null
  confidence: number
}

export interface InsightReportResult {
  overview: string
  insights: InsightResult[]
  limitations: string[]
}
