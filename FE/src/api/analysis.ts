import apiClient from '@/utils/apiClient'

export type AnalysisMode = 'BFS' | 'LLM'

export type AnalysisStatus = 'QUEUED' | 'PROCESSING' | 'COMPLETED' | 'FAILED'

export interface AnalysisSubmission {
  analysisId: string
  status: AnalysisStatus
  mode: AnalysisMode
  originalFilename: string
  sizeBytes: number
  createdAt: string
}

export interface FormulaResult {
  cell: string
  formula: string
  references: string[]
}

export interface RegionResult {
  startCell: string
  endCell: string
  cellCount: number
}

export interface SheetResult {
  name: string
  rows: number
  columns: number
  formulaCount: number
  tableCount: number
  chartCount: number
  formulas: FormulaResult[]
  regionCount: number
  regions: RegionResult[]
}

export interface WorkbookResult {
  filename: string
  sheetCount: number
  sheets: SheetResult[]
}

export interface AnalysisResultDetails {
  analysisId: string
  createdAt: string
  workbook: WorkbookResult
}

export interface CompletedAnalysis {
  submission: AnalysisSubmission
  result: AnalysisResultDetails
}

export const submitAnalysis = async (file: File, mode: AnalysisMode) => {
  const formData = new FormData()
  formData.append('file', file)
  formData.append('mode', mode)

  const { data } = await apiClient.post<AnalysisSubmission>('/api/v1/analyses', formData)
  return data
}

export const getAnalysisResult = async (analysisId: string) => {
  const { data } = await apiClient.get<AnalysisResultDetails>(
    `/api/v1/analyses/${analysisId}/result`,
  )
  return data
}

export const analyzeWorkbook = async (
  file: File,
  mode: AnalysisMode,
): Promise<CompletedAnalysis> => {
  const submission = await submitAnalysis(file, mode)
  const result = await getAnalysisResult(submission.analysisId)

  return { submission, result }
}
