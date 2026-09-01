import { ChevronDown, FileSpreadsheet } from 'lucide-react'

import type { SheetResult } from '@/api/analysis'
import SheetChartDetails from '@/components/analysis/workbook/details/SheetChartDetails'
import SheetFormulaDetails from '@/components/analysis/workbook/details/SheetFormulaDetails'
import SheetRegionDetails from '@/components/analysis/workbook/details/SheetRegionDetails'
import SheetTableDetails from '@/components/analysis/workbook/details/SheetTableDetails'
import SheetAtAGlance from '@/components/analysis/workbook/explorer/SheetAtAGlance'
import SheetColumnSchema from '@/components/analysis/workbook/schema/SheetColumnSchema'
import SheetSemanticSummary from '@/components/analysis/workbook/semantic/summaries/SheetSemanticSummary'

interface SheetResultCardProps {
  sheet: SheetResult
}

const SheetResultCard = ({ sheet }: SheetResultCardProps) => {
  const regions = sheet.regions ?? []
  const formulas = sheet.formulas ?? []
  const tables = sheet.tables ?? []
  const charts = sheet.charts ?? []
  const columns = sheet.columnSchemas ?? []
  const metrics = [
    ['데이터 영역', sheet.regionCount],
    ['수식', sheet.formulaCount],
    ['테이블', sheet.tableCount],
    ['차트', sheet.chartCount],
  ].filter(([, count]) => Number(count) > 0)
  const hasDetails =
    regions.length > 0 ||
    formulas.length > 0 ||
    tables.length > 0 ||
    charts.length > 0 ||
    columns.length > 0

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
          {metrics.map(([label, count]) => (
            <span className="rounded-lg bg-slate-50 px-2.5 py-1.5" key={label}>
              {label} {count}
            </span>
          ))}
        </div>
      </header>

      <SheetAtAGlance sheet={sheet} />

      {hasDetails && (
        <details className="group border-t border-slate-100">
          <summary className="flex cursor-pointer list-none items-center justify-between gap-4 px-5 py-4 marker:hidden">
            <div>
              <p className="text-sm font-extrabold text-slate-700">상세 분석 보기</p>
              <p className="mt-1 text-[11px] text-slate-400">
                AI 판단 근거와 전체 영역, 수식·열·표·차트를 확인합니다.
              </p>
            </div>
            <ChevronDown
              aria-hidden="true"
              className="shrink-0 text-slate-400 transition group-open:rotate-180"
              size={18}
            />
          </summary>
          <div className="border-t border-slate-100 bg-slate-50/40">
            <SheetSemanticSummary sheet={sheet} />
            <SheetColumnSchema
              columns={columns}
              key={sheet.name}
              sheetName={sheet.name}
            />

            <div className="space-y-4 p-5">
              {(regions.length > 0 || formulas.length > 0) && (
                <div
                  className={`grid gap-4 ${regions.length > 0 && formulas.length > 0 ? 'xl:grid-cols-2' : ''}`}
                >
                  <SheetRegionDetails regions={regions} sheetName={sheet.name} />
                  <SheetFormulaDetails formulas={formulas} sheetName={sheet.name} />
                </div>
              )}
              {(tables.length > 0 || charts.length > 0) && (
                <div
                  className={`grid gap-4 ${tables.length > 0 && charts.length > 0 ? 'xl:grid-cols-2' : ''}`}
                >
                  <SheetTableDetails tables={tables} sheetName={sheet.name} />
                  <SheetChartDetails charts={charts} sheetName={sheet.name} />
                </div>
              )}
            </div>
          </div>
        </details>
      )}
    </article>
  )
}

export default SheetResultCard
