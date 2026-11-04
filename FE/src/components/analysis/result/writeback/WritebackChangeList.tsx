import { useMemo } from 'react'

import type { WritebackChange } from '@/api/analysis'
import WritebackChangeCard from '@/components/analysis/result/writeback/WritebackChangeCard'
import WritebackMoreChanges from '@/components/analysis/result/writeback/WritebackMoreChanges'
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
  const keys = allChangeKeys(changes)
  const sheetCount = new Set(
    changes.flatMap((change) => [
      change.sheetName,
      ...(change.relatedCells ?? []).map((related) => related.sheetName),
    ]),
  ).size
  const formulaCount = changes.filter((change) => change.changeType === 'formula').length
  const allSelected = selectable && selected.length === keys.length
  // 조건으로 고른 수정은 수천 행이 될 수 있어 선택 확인은 집합으로 한다.
  const chosen = useMemo(() => new Set(selected), [selected])

  const card = (change: WritebackChange) => {
    const key = changeKey(change)
    return (
      <WritebackChangeCard
        change={change}
        key={key}
        onToggle={() => onToggle?.(key)}
        onToggleRelated={(item) => onToggle?.(item)}
        selectable={selectable}
        selected={!selectable || chosen.has(key)}
        selectedKeys={selected}
      />
    )
  }

  return (
    <div className="mt-4">
      <div className="mb-3 flex flex-wrap items-center gap-2 text-xs font-extrabold text-slate-600">
        <span className="rounded-full bg-white px-3 py-1.5 shadow-sm">
          {selectable
            ? `선택 ${selected.length} / ${keys.length}개`
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
        {selectable && keys.length > 1 && (
          <button
            className="ml-auto rounded-lg px-2 py-1 text-xs font-bold text-brand-700 underline-offset-4 transition hover:underline"
            onClick={() => onSelectAll?.(allSelected ? [] : keys)}
            type="button"
          >
            {allSelected ? '전체 해제' : '전체 선택'}
          </button>
        )}
      </div>
      <div className="space-y-3">{visible.map(card)}</div>
      {remaining.length > 0 && <WritebackMoreChanges items={remaining} render={card} />}
    </div>
  )
}

export default WritebackChangeList
