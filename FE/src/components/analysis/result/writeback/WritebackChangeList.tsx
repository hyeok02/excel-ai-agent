import { ChevronDown } from 'lucide-react'

import type { WritebackChange } from '@/api/analysis'
import WritebackChangeCard from '@/components/analysis/result/writeback/WritebackChangeCard'
import {
  allChangeKeys,
  changeKey,
} from '@/components/analysis/result/writeback/writebackSelection'

interface Props {
  changes: WritebackChange[]
  selectable?: boolean
  selected?: string[]
  onToggle?: (key: string) => void
  onSelectAll?: (keys: string[]) => void
}

const WritebackChangeList = ({
  changes,
  selectable = false,
  selected = [],
  onToggle,
  onSelectAll,
}: Props) => {
  const visible = changes.slice(0, 4)
  const remaining = changes.slice(4)
  const sheetCount = new Set(changes.map((change) => change.sheetName)).size
  const formulaCount = changes.filter((change) => change.changeType === 'formula').length
  const allSelected = selectable && selected.length === changes.length

  const card = (change: WritebackChange) => {
    const key = changeKey(change)
    return (
      <WritebackChangeCard
        change={change}
        key={key}
        onToggle={() => onToggle?.(key)}
        selectable={selectable}
        selected={!selectable || selected.includes(key)}
      />
    )
  }

  return (
    <div className="mt-4">
      <div className="mb-3 flex flex-wrap items-center gap-2 text-xs font-extrabold text-slate-600">
        <span className="rounded-full bg-white px-3 py-1.5 shadow-sm">
          {selectable
            ? `선택 ${selected.length} / ${changes.length}개`
            : `변경 ${changes.length}개`}
        </span>
        <span className="rounded-full bg-white px-3 py-1.5 shadow-sm">
          시트 {sheetCount}개
        </span>
        {formulaCount > 0 && (
          <span className="rounded-full bg-amber-50 px-3 py-1.5 text-amber-700">
            수식 {formulaCount}개
          </span>
        )}
        {selectable && changes.length > 1 && (
          <button
            className="ml-auto rounded-lg px-2 py-1 text-xs font-bold text-brand-700 underline-offset-4 transition hover:underline"
            onClick={() => onSelectAll?.(allSelected ? [] : allChangeKeys(changes))}
            type="button"
          >
            {allSelected ? '전체 해제' : '전체 선택'}
          </button>
        )}
      </div>
      <div className="space-y-3">{visible.map(card)}</div>
      {remaining.length > 0 && (
        <details className="group mt-3 rounded-2xl border border-slate-200 bg-white p-3">
          <summary className="flex cursor-pointer list-none items-center justify-between text-xs font-extrabold text-slate-600">
            나머지 변경 {remaining.length}개 확인
            <ChevronDown className="transition group-open:rotate-180" size={16} />
          </summary>
          <div className="mt-3 space-y-3">{remaining.map(card)}</div>
        </details>
      )}
    </div>
  )
}

export default WritebackChangeList
