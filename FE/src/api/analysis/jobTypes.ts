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
  sourceAvailable: boolean
  updatedAt: string
  failureMessage?: string | null
}

export interface AnalysisHistoryPage {
  content: AnalysisDetails[]
  page: number
  size: number
  totalElements: number
  totalPages: number
  hasNext: boolean
}

export interface AnalysisHistoryQuery {
  filename?: string
  mode?: AnalysisMode
  page?: number
  size?: number
}

export interface AnalysisResultDetails {
  analysisId: string
  createdAt: string
  sourceAvailable: boolean
  workbook: WorkbookResult
  insightReport: InsightReportResult | null
}

export interface CompletedAnalysis {
  submission: AnalysisSubmission
  result: AnalysisResultDetails
}
