import type { FormulaRiskSummaryResult } from '@/api/analysis'

interface FormulaRiskOverviewProps {
  summary: FormulaRiskSummaryResult
}

const FormulaRiskOverview = ({ summary }: FormulaRiskOverviewProps) => {
  const items = [
    ['계산 오류', summary.cachedErrorCount, '결과가 #N/A·#DIV/0! 로 남은 셀'],
    [
      '끊어질 수 있는 참조',
      summary.brokenReferenceCount +
        summary.missingSheetCount +
        summary.externalReferenceCount +
        summary.dynamicFunctionCount,
      '깨진 참조, 외부 파일, 동적 함수',
    ],
    ['참고 항목', summary.infoCount, '주변과 다른 수식, 직접 입력된 값'],
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
