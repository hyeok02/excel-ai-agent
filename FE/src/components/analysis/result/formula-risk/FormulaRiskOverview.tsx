import type { FormulaRiskSummaryResult } from '@/api/analysis'

interface FormulaRiskOverviewProps {
  summary: FormulaRiskSummaryResult
}

const FormulaRiskOverview = ({ summary }: FormulaRiskOverviewProps) => {
  const priorityCount = summary.criticalRiskCount + summary.highRiskCount
  const items = [
    ['우선 확인', priorityCount, '영향 범위가 큰 항목'],
    ['반복 수식 이상', summary.patternMismatchCount, '주변과 다른 계산식'],
    ['직접 입력 의심', summary.hardcodedValueCount, '수식 사이에 입력된 값'],
  ] as const

  return (
    <div className="grid gap-3 border-b border-blue-100 p-5 sm:grid-cols-3">
      {items.map(([label, count, description]) => (
        <div className="rounded-2xl border border-slate-200 bg-white p-4" key={label}>
          <p className="text-xs font-bold text-slate-500">{label}</p>
          <p className="mt-1 text-2xl font-black text-slate-950">{count}건</p>
          <p className="mt-1 text-xs text-slate-500">{description}</p>
        </div>
      ))}
    </div>
  )
}

export default FormulaRiskOverview
