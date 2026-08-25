export type InsightCategory = 'summary' | 'structure' | 'formula' | 'risk'
export type InsightSeverity = 'info' | 'warning' | 'critical'

export interface InsightResult {
  title: string
  description: string
  category: InsightCategory
  severity: InsightSeverity
  evidence: string[]
  recommendation: string | null
}

export interface InsightReportResult {
  overview: string
  insights: InsightResult[]
  limitations: string[]
}
