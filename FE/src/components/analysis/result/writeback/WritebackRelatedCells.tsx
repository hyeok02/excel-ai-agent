import { ArrowRight, Unlink } from 'lucide-react'

import type { WritebackRelatedCell } from '@/api/analysis'
import { relatedKey } from '@/components/analysis/result/writeback/writebackSelection'
import { showValue } from '@/components/analysis/result/writeback/writebackValue'

const KIND_LABEL = { total: '같은 행의 합계', mirror: '다른 시트의 같은 값' }

interface Props {
  cells: WritebackRelatedCell[]
  selectable: boolean
  selected: string[]
  onToggle: (key: string) => void
}

const WritebackRelatedCells = ({ cells, selectable, selected, onToggle }: Props) => (
  <div className="mt-3 rounded-2xl border border-amber-200 bg-amber-50/70 p-3">
    <p className="flex items-center gap-1.5 text-xs font-extrabold text-amber-900">
      <Unlink size={13} /> 수식으로 이어져 있지 않아 같이 확인할 셀 {cells.length}개
    </p>
    <div className="mt-2 space-y-2">
      {cells.map((cell) => {
        const key = relatedKey(cell)
        const checked = !selectable || selected.includes(key)
        return (
          <div className="rounded-xl bg-white/80 p-2.5" key={key}>
            <label className="flex min-w-0 items-center gap-2.5">
              {selectable && (
                <input
                  aria-label={`${key} 함께 수정`}
                  checked={checked}
                  className="size-4 shrink-0 cursor-pointer accent-amber-600"
                  onChange={() => onToggle(key)}
                  type="checkbox"
                />
              )}
              <span className="rounded-lg bg-amber-100 px-2 py-0.5 font-mono text-[11px] font-bold text-amber-800">
                {key}
              </span>
              <span className="text-[11px] font-bold text-amber-700">
                {KIND_LABEL[cell.kind]}
              </span>
            </label>
            <div className="mt-2 flex flex-wrap items-center gap-1.5 text-xs font-bold">
              <span className="rounded-lg bg-slate-100 px-2 py-1 text-slate-600">
                {showValue(cell.currentValue)}
              </span>
              <ArrowRight aria-hidden="true" className="text-slate-400" size={13} />
              <span className="rounded-lg bg-emerald-50 px-2 py-1 text-emerald-700">
                {showValue(cell.suggestedValue)}
              </span>
            </div>
            <p className="mt-1.5 whitespace-pre-line text-[11px] leading-5 text-amber-900/80">
              {cell.reason}
            </p>
          </div>
        )
      })}
    </div>
  </div>
)

export default WritebackRelatedCells
