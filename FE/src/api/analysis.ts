import apiClient from '@/utils/apiClient'

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

export interface FormulaResult {
  cell: string
  formula: string
  references: string[]
  cachedValue: CellValue
  role: 'calculation' | 'lookup' | 'presentation' | 'external'
}

export type CellValue = string | number | boolean | null

export interface CellResult {
  address: string
  value: CellValue
  formula: string | null
  cachedValue: CellValue
  numberFormat: string | null
  bold: boolean
  fillColor: string | null
  horizontalAlignment: string | null
  merged: boolean
}

export interface HeaderPathResult {
  column: string
  labels: string[]
}

export interface RegionResult {
  startCell: string
  endCell: string
  cellCount: number
  title: string | null
  rowCount: number
  columnCount: number
  mergedRanges: string[]
  headerPaths: HeaderPathResult[]
  previewRows: CellResult[][]
  truncated: boolean
}

export interface TableResult {
  name: string
  displayName: string
  reference: string
  headers: string[]
  rowCount: number
  columnCount: number
  previewRows: CellResult[][]
  truncated: boolean
}

export interface ChartSeriesResult {
  title: string | null
  categoriesReference: string | null
  valuesReference: string | null
  categorySamples: CellValue[]
  valueSamples: CellValue[]
}

export interface ChartResult {
  title: string | null
  chartType: string
  anchorCell: string | null
  seriesCount: number
  series: ChartSeriesResult[]
  truncated: boolean
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
  tables: TableResult[]
  charts: ChartResult[]
}

export type DependencyNodeKind = 'formula' | 'cell' | 'range' | 'named' | 'external'

export interface DependencyNodeResult {
  id: string
  label: string
  sheet: string | null
  cell: string | null
  kind: DependencyNodeKind
  formula: string | null
}

export interface DependencyEdgeResult {
  source: string
  target: string
  reference: string
  crossSheet: boolean
}

export interface DependencyClusterResult {
  id: string
  nodeCount: number
  edgeCount: number
  formulaCount: number
  sheetNames: string[]
  nodes: DependencyNodeResult[]
  edges: DependencyEdgeResult[]
  truncated: boolean
}

export interface DependencyGraphResult {
  nodeCount: number
  edgeCount: number
  formulaNodeCount: number
  crossSheetEdgeCount: number
  namedReferenceCount: number
  externalReferenceCount: number
  clusterCount: number
  clusters: DependencyClusterResult[]
}

export interface WorkbookResult {
  filename: string
  sheetCount: number
  sheets: SheetResult[]
  dependencyGraph?: DependencyGraphResult | null
}

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

export const submitAnalysis = async (
  file: File,
  mode: AnalysisMode,
  depth: AnalysisDepth,
) => {
  const formData = new FormData()
  formData.append('file', file)
  formData.append('mode', mode)
  formData.append('depth', depth)

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
  depth: AnalysisDepth,
): Promise<CompletedAnalysis> => {
  const submission = await submitAnalysis(file, mode, depth)
  const result = await getAnalysisResult(submission.analysisId)

  return { submission, result }
}
