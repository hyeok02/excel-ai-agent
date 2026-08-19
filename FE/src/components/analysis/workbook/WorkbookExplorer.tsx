import { useMemo, useState } from 'react'

import type { SheetResult } from '@/api/analysis'
import SheetResultCard from '@/components/analysis/workbook/SheetResultCard'

interface WorkbookExplorerProps {
  sheets: SheetResult[]
}

const WorkbookExplorer = ({ sheets }: WorkbookExplorerProps) => {
  const [selectedSheetName, setSelectedSheetName] = useState(sheets[0]?.name ?? '')
  const selectedSheet = useMemo(
    () => sheets.find((sheet) => sheet.name === selectedSheetName) ?? sheets[0],
    [selectedSheetName, sheets],
  )

  if (!selectedSheet) return null

  return (
    <section className="mt-6">
      <div className="mb-3 flex flex-wrap items-end justify-between gap-3">
        <div>
          <p className="text-xs font-extrabold tracking-[0.16em] text-brand-600">
            WORKBOOK EXPLORER
          </p>
          <h2 className="mt-1 text-lg font-extrabold text-slate-900">
            시트별 구조와 원본 위치
          </h2>
          <p className="mt-1 text-xs leading-5 text-slate-500">
            시트를 선택하면 데이터 영역, 수식, 표와 차트를 함께 확인할 수 있어요.
          </p>
        </div>
        <span className="rounded-xl bg-slate-50 px-3 py-2 text-xs font-bold text-slate-500">
          전체 {sheets.length}개 시트
        </span>
      </div>

      <div
        aria-label="Excel 시트 선택"
        className="mb-3 flex gap-2 overflow-x-auto rounded-2xl bg-slate-50 p-2"
        role="tablist"
      >
        {sheets.map((sheet) => {
          const selected = sheet.name === selectedSheet.name
          return (
            <button
              aria-selected={selected}
              className={`shrink-0 rounded-xl px-4 py-2.5 text-left text-xs font-bold transition ${
                selected
                  ? 'bg-white text-brand-700 shadow-sm ring-1 ring-slate-200'
                  : 'text-slate-500 hover:bg-white/70 hover:text-slate-700'
              }`}
              key={sheet.name}
              onClick={() => setSelectedSheetName(sheet.name)}
              role="tab"
              type="button"
            >
              {sheet.name}
              <span className="ml-2 font-medium text-slate-400">
                {sheet.rows.toLocaleString()}×{sheet.columns.toLocaleString()}
              </span>
            </button>
          )
        })}
      </div>

      <SheetResultCard key={selectedSheet.name} sheet={selectedSheet} />
    </section>
  )
}

export default WorkbookExplorer
