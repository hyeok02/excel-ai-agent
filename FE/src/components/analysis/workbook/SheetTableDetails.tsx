import { Table2 } from 'lucide-react'

import type { TableResult } from '@/api/analysis'
import CellPreviewTable from '@/components/analysis/workbook/CellPreviewTable'
import OriginalLocationButton from '@/components/analysis/workbook/OriginalLocationButton'

interface SheetTableDetailsProps {
  tables: TableResult[]
  sheetName: string
}

const SheetTableDetails = ({ tables, sheetName }: SheetTableDetailsProps) => {
  if (tables.length === 0) return null

  return (
    <section className="rounded-2xl border border-slate-200 bg-white p-4">
      <div className="flex items-center justify-between gap-3">
        <div className="flex items-center gap-2">
          <Table2 aria-hidden="true" className="text-brand-600" size={16} />
          <h4 className="text-xs font-extrabold tracking-wide text-slate-700">
            Excel 테이블 상세
          </h4>
        </div>
        <span className="rounded-lg bg-brand-50 px-2.5 py-1 text-[11px] font-bold text-brand-700">
          {tables.length}개
        </span>
      </div>

      <div className="mt-3 space-y-3">
        {tables.map((table, index) => (
          <details
            className="rounded-xl bg-slate-50/80"
            key={`${table.name}-${table.reference}`}
            open={index === 0}
          >
            <summary className="flex cursor-pointer list-none flex-wrap items-center justify-between gap-3 px-4 py-3 marker:hidden">
              <div>
                <p className="text-sm font-extrabold text-slate-800">{table.displayName}</p>
                <p className="mt-1 text-[11px] text-slate-400">
                  {table.reference} · {table.rowCount.toLocaleString()}행 ×{' '}
                  {table.columnCount.toLocaleString()}열
                </p>
              </div>
              <div className="flex flex-wrap gap-1.5">
                {table.headers.slice(0, 6).map((header, headerIndex) => (
                  <span
                    className="rounded-md bg-white px-2 py-1 text-[10px] font-semibold text-slate-500"
                    key={`${header}-${headerIndex}`}
                  >
                    {header}
                  </span>
                ))}
                {table.headers.length > 6 && (
                  <span className="rounded-md bg-white px-2 py-1 text-[10px] text-slate-400">
                    +{table.headers.length - 6}
                  </span>
                )}
              </div>
            </summary>
            <div className="border-t border-slate-200 p-3">
              <div className="mb-3 flex justify-end">
                <OriginalLocationButton location={table.reference} sheetName={sheetName} />
              </div>
              <CellPreviewTable rows={table.previewRows ?? []} />
              {table.truncated && (
                <p className="mt-2 text-[11px] text-slate-400">
                  큰 테이블은 앞쪽 8행 × 12열만 표시합니다.
                </p>
              )}
            </div>
          </details>
        ))}
      </div>
    </section>
  )
}

export default SheetTableDetails
