import type { DependencyGraphResult } from '@/api/analysis/dependencyTypes'
import type {
  AnalysisInclusion,
  SemanticClassification,
  SheetClassification,
} from '@/api/analysis/semanticTypes'

export type CellValue = string | number | boolean | null

export interface FormulaResult {
  cell: string
  formula: string
  references: string[]
  cachedValue: CellValue
  role: 'calculation' | 'lookup' | 'presentation' | 'external'
}

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
  semantic: SemanticClassification | null
}

export interface HeaderPathResult {
  column: string
  labels: string[]
}

export interface ColumnSchemaResult {
  column: string
  sourceRange: string
  headerPath: string[]
  displayName: string
  standardField: string
  dataType: string
  unitType: string
  unitLabel: string | null
  confidence: number
  evidence: string[]
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
  semantic: SemanticClassification | null
  analysisInclusion: AnalysisInclusion | null
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
  columnSchemas?: ColumnSchemaResult[]
  tables: TableResult[]
  charts: ChartResult[]
  analysisInclusion: AnalysisInclusion | null
  sheetClassification: SheetClassification | null
}

export interface ExcludedSheetResult {
  name: string
  state: string
  analysisInclusion: AnalysisInclusion
  sheetClassification: SheetClassification | null
}

export interface WorkbookResult {
  filename: string
  sheetCount: number
  totalSheetCount: number
  excludedSheetCount: number
  excludedSheets: ExcludedSheetResult[]
  sheets: SheetResult[]
  dependencyGraph?: DependencyGraphResult | null
}
