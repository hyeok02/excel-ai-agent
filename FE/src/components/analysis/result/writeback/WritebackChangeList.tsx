import { ArrowRight, ChevronDown, Sigma } from 'lucide-react'

import type { WritebackChange } from '@/api/analysis'
import OriginalLocationButton from '@/components/analysis/workbook/details/OriginalLocationButton'

const show = (value: WritebackChange['oldValue'] | WritebackChange['newValue']) => {
  if (value === null) return '(빈 셀)'
  if (typeof value === 'boolean') return value ? 'TRUE' : 'FALSE'
  return String(value)
}

const riskLabel = {
  low: '낮은 영향',
  medium: '영향 확인',
  high: '높은 영향',
}

const ChangeCard = ({ change }: { change: WritebackChange }) => (
      <div
        className="rounded-2xl border border-slate-200 bg-white p-4"
      >
        <div className="flex flex-wrap items-center justify-between gap-2">
          <span className="rounded-lg bg-brand-50 px-2.5 py-1 font-mono text-xs font-bold text-brand-700">
            {change.sheetName}!{change.reference}
          </span>
          <OriginalLocationButton
            location={change.reference}
            sheetName={change.sheetName}
          />
        </div>
        {(change.riskLevel || change.changeType === 'formula') && (
          <div className="mt-2 flex flex-wrap items-center gap-2 text-[11px] font-bold">
            <span
              className={`rounded-full px-2 py-1 ${
                change.riskLevel === 'high'
                  ? 'bg-red-50 text-red-700'
                  : change.riskLevel === 'medium'
                    ? 'bg-amber-50 text-amber-700'
                    : 'bg-slate-100 text-slate-500'
              }`}
            >
              {riskLabel[change.riskLevel ?? 'low']}
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
        <p className="mt-2 text-xs leading-5 text-slate-500">
          변경 이유: {change.reason}
        </p>
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
            <Sigma size={13} /> 이 값을 참조하는 수식 {change.affectedCells.length}개가 다시 계산됩니다.
          </p>
        )}
      </div>
)

const WritebackChangeList = ({ changes }: { changes: WritebackChange[] }) => {
  const visible = changes.slice(0, 4)
  const remaining = changes.slice(4)
  const sheetCount = new Set(changes.map((change) => change.sheetName)).size
  const formulaCount = changes.filter((change) => change.changeType === 'formula').length

  return (
  <div className="mt-4">
    <div className="mb-3 flex flex-wrap gap-2 text-xs font-extrabold text-slate-600">
      <span className="rounded-full bg-white px-3 py-1.5 shadow-sm">변경 {changes.length}개</span>
      <span className="rounded-full bg-white px-3 py-1.5 shadow-sm">시트 {sheetCount}개</span>
      {formulaCount > 0 && (
        <span className="rounded-full bg-amber-50 px-3 py-1.5 text-amber-700">
          수식 {formulaCount}개
        </span>
      )}
    </div>
    <div className="space-y-3">
      {visible.map((change) => (
        <ChangeCard change={change} key={`${change.sheetName}-${change.reference}`} />
      ))}
    </div>
    {remaining.length > 0 && (
      <details className="group mt-3 rounded-2xl border border-slate-200 bg-white p-3">
        <summary className="flex cursor-pointer list-none items-center justify-between text-xs font-extrabold text-slate-600">
          나머지 변경 {remaining.length}개 확인
          <ChevronDown className="transition group-open:rotate-180" size={16} />
        </summary>
        <div className="mt-3 space-y-3">
          {remaining.map((change) => (
            <ChangeCard change={change} key={`${change.sheetName}-${change.reference}`} />
          ))}
        </div>
      </details>
    )}
  </div>
  )
}

export default WritebackChangeList
