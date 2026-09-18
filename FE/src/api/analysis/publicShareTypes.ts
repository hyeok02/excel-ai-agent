import type { InsightReportResult } from '@/api/analysis/insightTypes'
import type { WorkbookResult } from '@/api/analysis/workbookTypes'

export interface AnalysisPublicShareResult {
  createdAt: string
  expiresAt: string
  workbook: WorkbookResult
  insightReport: InsightReportResult | null
}
