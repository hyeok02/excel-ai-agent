import type { AnalysisMode, WorkbookResult } from '@/api/analysis'

export const MODE_PRESENTATION: Record<AnalysisMode, { completion: string }> = {
  BFS: {
    completion: '규칙 기반 분석 완료',
  },
  LLM: {
    completion: '파일 내용 및 인사이트 분석 완료',
  },
}

export const getWorkbookSummaryItems = (workbook: WorkbookResult) => {
  const totals = workbook.sheets.reduce(
    (summary, sheet) => ({
      regions: summary.regions + sheet.regionCount,
      formulas: summary.formulas + sheet.formulaCount,
      tables: summary.tables + sheet.tableCount,
      charts: summary.charts + sheet.chartCount,
    }),
    { regions: 0, formulas: 0, tables: 0, charts: 0 },
  )

  return [
    ['시트', workbook.sheetCount],
    ['데이터 영역', totals.regions],
    ['수식', totals.formulas],
    ['테이블', totals.tables],
    ['차트', totals.charts],
  ] as const
}
