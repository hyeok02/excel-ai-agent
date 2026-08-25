import type { InsightReportResult } from '@/api/analysis/insightTypes'
import type { WorkbookResult } from '@/api/analysis/workbookTypes'

export type AnalysisMode = 'BFS' | 'LLM'
export type AnalysisDepth = 'AUTO' | 'FAST' | 'PRECISE'
export type AnalysisStatus = 'QUEUED' | 'PROCESSING' | 'COMPLETED' | 'FAILED'

export interface AnalysisSubmission {
  analysisId: string
  status: AnalysisStatus
  mode: AnalysisMode
  originalFilename: string
  sizeBytes: number
  createdAt: string
}

export interface AnalysisDetails extends AnalysisSubmission {
  fileExtension: string
  updatedAt: string
}

export interface AnalysisResultDetails {
  analysisId: string
  createdAt: string
  workbook: WorkbookResult
  insightReport: InsightReportResult | null
}

export interface CompletedAnalysis {
  submission: AnalysisSubmission
  result: AnalysisResultDetails
}
