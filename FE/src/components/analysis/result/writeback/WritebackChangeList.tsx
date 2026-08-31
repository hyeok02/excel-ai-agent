import { ArrowRight } from 'lucide-react'

import type { WritebackChange } from '@/api/analysis'

const show = (value: WritebackChange['oldValue'] | WritebackChange['newValue']) => {
  if (value === null) return '(빈 셀)'
  if (typeof value === 'boolean') return value ? 'TRUE' : 'FALSE'
  return String(value)
}

const WritebackChangeList = ({ changes }: { changes: WritebackChange[] }) => (
  <div className="mt-4 space-y-3">
    {changes.map((change) => (
      <div className="rounded-2xl border border-slate-200 bg-white p-4" key={`${change.sheetName}-${change.reference}`}>
        <div className="flex flex-wrap items-center justify-between gap-2">
          <span className="rounded-lg bg-brand-50 px-2.5 py-1 font-mono text-xs font-bold text-brand-700">
            {change.sheetName}!{change.reference}
          </span>
          <span className="text-xs font-semibold text-slate-400">원본 파일에서 확인됨</span>
        </div>
        <div className="mt-3 flex flex-wrap items-center gap-2 text-sm font-bold">
          <span className="rounded-xl bg-slate-100 px-3 py-2 text-slate-600">{show(change.oldValue)}</span>
          <ArrowRight aria-hidden="true" className="text-slate-400" size={16} />
          <span className="rounded-xl bg-emerald-50 px-3 py-2 text-emerald-700">{show(change.newValue)}</span>
        </div>
        <p className="mt-2 text-xs leading-5 text-slate-500">변경 이유: {change.reason}</p>
      </div>
    ))}
  </div>
)

export default WritebackChangeList
