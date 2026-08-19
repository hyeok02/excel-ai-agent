import { CheckCircle2 } from 'lucide-react'

import type { AnalysisResultDetails, WorkbookResult } from '@/api/analysis'
import AnalysisExportActions from '@/components/analysis/AnalysisExportActions'
import InsightReportSection from '@/components/analysis/InsightReportSection'
import SheetResultCard from '@/components/analysis/SheetResultCard'

interface AnalysisResultSectionProps {
  result: AnalysisResultDetails
}

const getWorkbookTotals = (workbook: WorkbookResult) => {
  return workbook.sheets.reduce(
    (totals, sheet) => ({
      regions: totals.regions + sheet.regionCount,
      formulas: totals.formulas + sheet.formulaCount,
      tables: totals.tables + sheet.tableCount,
      charts: totals.charts + sheet.chartCount,
    }),
    { regions: 0, formulas: 0, tables: 0, charts: 0 },
  )
}

const AnalysisResultSection = ({ result }: AnalysisResultSectionProps) => {
  const { workbook } = result
  const totals = getWorkbookTotals(workbook)
  const summaryItems = [
    ['시트', workbook.sheetCount],
    ['데이터 영역', totals.regions],
    ['수식', totals.formulas],
    ['테이블', totals.tables],
    ['차트', totals.charts],
  ] as const

  return (
    <section className="panel p-5 md:p-7" aria-live="polite">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <div className="flex items-center gap-2 text-emerald-600">
            <CheckCircle2 aria-hidden="true" size={18} />
            <span className="text-xs font-extrabold tracking-wide">분석 완료</span>
          </div>
          <h2 className="mt-2 text-xl font-extrabold tracking-tight text-slate-950">
            {workbook.filename}
          </h2>
          <p className="mt-1 text-sm text-slate-500">분석 ID {result.analysisId}</p>
        </div>
        <div className="flex flex-col items-start gap-3 sm:items-end">
          <span className="rounded-xl bg-slate-50 px-3 py-2 text-xs font-semibold text-slate-500">
            {new Date(result.createdAt).toLocaleString('ko-KR')}
          </span>
          <AnalysisExportActions result={result} />
        </div>
      </div>

      <div className="mt-6 grid gap-3 sm:grid-cols-2 xl:grid-cols-5">
        {summaryItems.map(([label, value]) => (
          <div className="rounded-2xl bg-slate-50 p-4" key={label}>
            <p className="text-xs font-semibold text-slate-400">{label}</p>
            <p className="mt-2 text-2xl font-extrabold tracking-tight text-slate-900">
              {value.toLocaleString()}
            </p>
          </div>
        ))}
      </div>

      {result.insightReport && <InsightReportSection report={result.insightReport} />}

      <div className="mt-6 space-y-3">
        {workbook.sheets.map((sheet) => (
          <SheetResultCard key={sheet.name} sheet={sheet} />
        ))}
      </div>
    </section>
  )
}

export default AnalysisResultSection
