import { AlertCircle, AlertTriangle } from 'lucide-react'

import type { FormulaRiskFindingResult } from '@/api/analysis'
import FormulaDisclosure from '@/components/analysis/result/dependency/FormulaDisclosure'
import { FORMULA_RISK_PRESENTATION } from '@/components/analysis/result/formula-risk/formulaRiskPresentation'

interface FormulaRiskFindingCardProps {
  finding: FormulaRiskFindingResult
}

const FormulaRiskFindingCard = ({ finding }: FormulaRiskFindingCardProps) => {
  const presentation = FORMULA_RISK_PRESENTATION[finding.kind]
  const isError = finding.severity === 'error'
  const Icon = isError ? AlertCircle : AlertTriangle

  return (
    <article className="rounded-2xl border border-slate-200 bg-white p-4">
      <div className="flex items-start gap-3">
        <span
          className={`grid size-9 shrink-0 place-items-center rounded-xl ${
            isError ? 'bg-red-50 text-red-600' : 'bg-amber-50 text-amber-600'
          }`}
        >
          <Icon aria-hidden="true" size={17} />
        </span>
        <div className="min-w-0 flex-1">
          <div className="flex flex-wrap items-center justify-between gap-2">
            <h4 className="font-extrabold text-slate-900">{presentation.label}</h4>
            <span className="rounded-lg bg-slate-100 px-2 py-1 font-mono text-[11px] font-bold text-slate-600">
              {finding.sheetName}!{finding.cell}
            </span>
          </div>
          <p className="mt-1 text-sm leading-6 text-slate-600">{finding.message}</p>
          <p className="mt-2 text-xs font-bold text-slate-700">{presentation.action}</p>
          <FormulaDisclosure formula={finding.formula} />
        </div>
      </div>
    </article>
  )
}

export default FormulaRiskFindingCard
