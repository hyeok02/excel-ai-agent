import { FileSpreadsheet } from 'lucide-react'

import type { SheetResult } from '@/api/analysis'
import SheetChartDetails from '@/components/analysis/workbook/details/SheetChartDetails'
import SheetFormulaDetails from '@/components/analysis/workbook/details/SheetFormulaDetails'
import SheetRegionDetails from '@/components/analysis/workbook/details/SheetRegionDetails'
import SheetTableDetails from '@/components/analysis/workbook/details/SheetTableDetails'

interface SheetResultCardProps {
  sheet: SheetResult
}

const SheetResultCard = ({ sheet }: SheetResultCardProps) => {
  return (
    <article className="rounded-2xl border border-slate-200 bg-white shadow-sm">
      <header className="flex flex-wrap items-center justify-between gap-4 p-5">
        <div className="flex min-w-0 items-center gap-3">
          <span className="grid size-10 shrink-0 place-items-center rounded-xl bg-brand-50 text-brand-700">
            <FileSpreadsheet aria-hidden="true" size={18} />
          </span>
          <div className="min-w-0">
            <h3 className="truncate text-sm font-extrabold text-slate-900">
              {sheet.name}
            </h3>
            <p className="mt-1 text-xs text-slate-500">
              {sheet.rows.toLocaleString()}행 × {sheet.columns.toLocaleString()}열
            </p>
          </div>
        </div>
        <div className="flex flex-wrap gap-2 text-xs font-semibold text-slate-500">
          <span className="rounded-lg bg-slate-50 px-2.5 py-1.5">
            영역 {sheet.regionCount}
          </span>
          <span className="rounded-lg bg-slate-50 px-2.5 py-1.5">
            수식 {sheet.formulaCount}
          </span>
          <span className="rounded-lg bg-slate-50 px-2.5 py-1.5">
            테이블 {sheet.tableCount}
          </span>
          <span className="rounded-lg bg-slate-50 px-2.5 py-1.5">
            차트 {sheet.chartCount}
          </span>
        </div>
      </header>

      <div className="space-y-4 border-t border-slate-100 p-5">
        <div className="grid gap-4 xl:grid-cols-2">
          <SheetRegionDetails regions={sheet.regions ?? []} sheetName={sheet.name} />
          <SheetFormulaDetails formulas={sheet.formulas ?? []} sheetName={sheet.name} />
        </div>
        <div className="grid gap-4 xl:grid-cols-2">
          <SheetTableDetails tables={sheet.tables ?? []} sheetName={sheet.name} />
          <SheetChartDetails charts={sheet.charts ?? []} sheetName={sheet.name} />
        </div>
      </div>
    </article>
  )
}

export default SheetResultCard
