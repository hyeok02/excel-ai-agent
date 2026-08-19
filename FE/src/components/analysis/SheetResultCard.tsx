import { FileSpreadsheet } from 'lucide-react'

import type { SheetResult } from '@/api/analysis'

interface SheetResultCardProps {
  sheet: SheetResult
}

const SheetResultCard = ({ sheet }: SheetResultCardProps) => {
  return (
    <details className="group rounded-2xl border border-slate-200 bg-white open:shadow-sm">
      <summary className="flex cursor-pointer list-none flex-wrap items-center justify-between gap-4 p-5 marker:hidden">
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
      </summary>

      <div className="grid gap-5 border-t border-slate-100 p-5 lg:grid-cols-2">
        <section>
          <h4 className="text-xs font-extrabold tracking-wide text-slate-700">
            탐지된 영역
          </h4>
          {sheet.regions.length > 0 ? (
            <div className="mt-3 max-h-64 space-y-2 overflow-auto pr-1">
              {sheet.regions.map((region, index) => (
                <div
                  className="flex items-center justify-between rounded-xl bg-slate-50 px-3 py-2.5 text-xs"
                  key={`${region.startCell}-${region.endCell}-${index}`}
                >
                  <span className="font-bold text-slate-700">
                    {region.startCell} : {region.endCell}
                  </span>
                  <span className="text-slate-400">
                    {region.cellCount.toLocaleString()}셀
                  </span>
                </div>
              ))}
            </div>
          ) : (
            <p className="mt-3 rounded-xl bg-slate-50 p-4 text-xs text-slate-400">
              탐지된 데이터 영역이 없습니다.
            </p>
          )}
        </section>

        <section>
          <h4 className="text-xs font-extrabold tracking-wide text-slate-700">
            수식과 참조 관계
          </h4>
          {sheet.formulas.length > 0 ? (
            <div className="mt-3 max-h-64 space-y-2 overflow-auto pr-1">
              {sheet.formulas.map((formula) => (
                <div className="rounded-xl bg-slate-50 p-3 text-xs" key={formula.cell}>
                  <div className="flex items-start gap-2">
                    <span className="shrink-0 rounded-md bg-white px-2 py-1 font-extrabold text-brand-700 shadow-sm">
                      {formula.cell}
                    </span>
                    <code className="break-all pt-1 leading-5 text-slate-600">
                      {formula.formula}
                    </code>
                  </div>
                  <p className="mt-2 break-all text-slate-400">
                    참조:{' '}
                    {formula.references.length > 0
                      ? formula.references.join(', ')
                      : '없음'}
                  </p>
                </div>
              ))}
            </div>
          ) : (
            <p className="mt-3 rounded-xl bg-slate-50 p-4 text-xs text-slate-400">
              분석할 수식이 없습니다.
            </p>
          )}
        </section>
      </div>
    </details>
  )
}

export default SheetResultCard
