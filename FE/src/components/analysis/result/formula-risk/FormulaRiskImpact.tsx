import type { FormulaRiskImpactResult } from '@/api/analysis'

interface FormulaRiskImpactProps {
  impact?: FormulaRiskImpactResult | null
}

const FormulaRiskImpact = ({ impact }: FormulaRiskImpactProps) => {
  if (!impact || impact.affectedFormulaCount === 0) {
    return (
      <p className="mt-3 rounded-xl bg-slate-50 px-3 py-2 text-xs text-slate-600">
        현재 확인된 후속 계산 영향은 없습니다.
      </p>
    )
  }

  const sheets = impact.affectedSheets.slice(0, 3).join(', ')
  const extraCount = impact.affectedSheets.length - 3

  return (
    <div className="mt-3 rounded-xl bg-blue-50 px-3 py-2.5">
      <p className="text-xs font-extrabold text-blue-900">
        계산 결과 {impact.affectedFormulaCount}개 · 시트 {impact.affectedSheetCount}개에 영향
      </p>
      <p className="mt-1 text-[11px] leading-5 text-blue-700">
        최대 {impact.maxDepth}단계까지 이어집니다.
        {sheets && ` 영향 시트: ${sheets}${extraCount > 0 ? ` 외 ${extraCount}개` : ''}`}
      </p>
    </div>
  )
}

export default FormulaRiskImpact
