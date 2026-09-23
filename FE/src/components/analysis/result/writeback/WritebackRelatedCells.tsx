import { ArrowRight, Unlink } from 'lucide-react'

import type { WritebackRelatedCell } from '@/api/analysis'
import { relatedKey } from '@/components/analysis/result/writeback/writebackSelection'
import { showValue } from '@/components/analysis/result/writeback/writebackValue'

const KIND_LABEL = { total: '같은 행의 합계', mirror: '다른 시트의 같은 값' }
const SUM_LABEL = ['지금', '바꾼 뒤']

interface Props {
  cells: WritebackRelatedCell[]
  sheetName: string
  selectable: boolean
  selected: string[]
  onToggle: (key: string) => void
}

const WritebackRelatedCells = ({
  cells,
  sheetName,
  selectable,
  selected,
  onToggle,
}: Props) => (
  <div className="mt-3 rounded-2xl border border-amber-200 bg-amber-50/60 p-3">
    <p className="flex items-center gap-1.5 px-1 text-xs font-extrabold text-amber-900">
      <Unlink size={13} /> 수식으로 이어져 있지 않아 같이 확인할 셀 {cells.length}개
    </p>
    <div className="mt-2 space-y-2">
      {cells.map((cell) => {
        const key = relatedKey(cell)
        return (
          <div className="rounded-xl bg-white p-3 shadow-sm" key={key}>
            <div className="flex flex-wrap items-center gap-2">
              <label className="flex min-w-0 items-center gap-2.5">
                {selectable && (
                  <input
                    aria-label={`${key} 함께 수정`}
                    checked={selected.includes(key)}
                    className="size-4 shrink-0 cursor-pointer accent-amber-600"
                    onChange={() => onToggle(key)}
                    type="checkbox"
                  />
                )}
                <span className="rounded-lg bg-amber-100 px-2 py-0.5 font-mono text-xs font-bold text-amber-900">
                  {cell.sheetName === sheetName ? cell.reference : key}
                </span>
                <span className="text-[11px] font-bold text-amber-700">
                  {KIND_LABEL[cell.kind]}
                </span>
              </label>
              <div className="ml-auto flex items-center gap-1.5 text-sm font-bold">
                <span className="rounded-lg bg-slate-100 px-2.5 py-1 text-slate-600">
                  {showValue(cell.currentValue)}
                </span>
                <ArrowRight aria-hidden="true" className="text-slate-400" size={14} />
                <span className="rounded-lg bg-emerald-50 px-2.5 py-1 text-emerald-700">
                  {showValue(cell.suggestedValue)}
                </span>
              </div>
            </div>
            <p className="mt-2.5 text-xs leading-5 text-slate-600">{cell.reason}</p>
            {cell.breakdown && cell.breakdown.length > 0 && (
              <div className="mt-2.5 space-y-1 rounded-lg bg-slate-50 px-3 py-2.5">
                {cell.breakdown.map((line, index) => (
                  <p className="flex gap-3" key={`${SUM_LABEL[index]}-${line}`}>
                    <span className="w-11 shrink-0 text-[11px] font-bold text-slate-400">
                      {SUM_LABEL[index]}
                    </span>
                    <span
                      className={`font-mono text-[11px] ${
                        index === 1 ? 'font-bold text-emerald-700' : 'text-slate-500'
                      }`}
                    >
                      {line}
                    </span>
                  </p>
                ))}
              </div>
            )}
            {cell.parts && cell.parts.length > 0 && (
              <p className="mt-2 text-[11px] leading-4 text-slate-400">
                더한 항목 · {cell.parts.join(' · ')}
              </p>
            )}
          </div>
        )
      })}
    </div>
  </div>
)

export default WritebackRelatedCells
