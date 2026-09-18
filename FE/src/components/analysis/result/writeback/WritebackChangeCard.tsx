import { ArrowRight, Sigma } from 'lucide-react'

import type { WritebackChange } from '@/api/analysis'
import OriginalLocationButton from '@/components/analysis/workbook/details/OriginalLocationButton'

const show = (value: WritebackChange['oldValue']) => {
  if (value === null) return '(빈 셀)'
  if (typeof value === 'boolean') return value ? 'TRUE' : 'FALSE'
  return String(value)
}

const RISK_LABEL = { low: '낮은 영향', medium: '영향 확인', high: '높은 영향' }
const RISK_CLASS = {
  low: 'bg-slate-100 text-slate-500',
  medium: 'bg-amber-50 text-amber-700',
  high: 'bg-red-50 text-red-700',
}

interface Props {
  change: WritebackChange
  selectable: boolean
  selected: boolean
  onToggle: () => void
}

const WritebackChangeCard = ({ change, selectable, selected, onToggle }: Props) => {
  const risk = change.riskLevel ?? 'low'
  return (
    <div
      className={`rounded-2xl border p-4 transition ${
        selectable && !selected
          ? 'border-slate-200 bg-slate-50/70 opacity-60'
          : 'border-slate-200 bg-white'
      }`}
    >
      <div className="flex flex-wrap items-center justify-between gap-2">
        <label className="flex min-w-0 items-center gap-2.5">
          {selectable && (
            <input
              aria-label={`${change.sheetName}!${change.reference} 변경 적용`}
              checked={selected}
              className="size-4 shrink-0 cursor-pointer accent-brand-600"
              onChange={onToggle}
              type="checkbox"
            />
          )}
          <span className="rounded-lg bg-brand-50 px-2.5 py-1 font-mono text-xs font-bold text-brand-700">
            {change.sheetName}!{change.reference}
          </span>
        </label>
        <OriginalLocationButton
          location={change.reference}
          sheetName={change.sheetName}
        />
      </div>
      {(change.riskLevel || change.changeType === 'formula') && (
        <div className="mt-2 flex flex-wrap items-center gap-2 text-[11px] font-bold">
          <span className={`rounded-full px-2 py-1 ${RISK_CLASS[risk]}`}>
            {RISK_LABEL[risk]}
          </span>
          {change.changeType === 'formula' && (
            <span className="rounded-full bg-brand-50 px-2 py-1 text-brand-700">
              수식 변경
            </span>
          )}
        </div>
      )}
      <div className="mt-3 flex flex-wrap items-center gap-2 text-sm font-bold">
        <span className="rounded-xl bg-slate-100 px-3 py-2 text-slate-600">
          {show(change.oldValue)}
        </span>
        <ArrowRight aria-hidden="true" className="text-slate-400" size={16} />
        <span className="rounded-xl bg-emerald-50 px-3 py-2 text-emerald-700">
          {show(change.newValue)}
        </span>
      </div>
      <p className="mt-2 text-xs leading-5 text-slate-500">변경 이유: {change.reason}</p>
      {change.contextCells && change.contextCells.length > 0 && (
        <p
          className="mt-2 truncate text-xs text-slate-400"
          title={change.contextCells
            .map((cell) => `${cell.reference} ${show(cell.value)}`)
            .join(' · ')}
        >
          주변 내용 ·{' '}
          {change.contextCells
            .slice(0, 3)
            .map((cell) => `${cell.reference} ${show(cell.value)}`)
            .join(' · ')}
        </p>
      )}
      {change.affectedCells && change.affectedCells.length > 0 && (
        <p className="mt-2 flex items-center gap-1.5 text-xs font-semibold text-amber-700">
          <Sigma size={13} /> 이 값을 참조하는 수식 {change.affectedCells.length}개가 다시
          계산됩니다.
        </p>
      )}
    </div>
  )
}

export default WritebackChangeCard
