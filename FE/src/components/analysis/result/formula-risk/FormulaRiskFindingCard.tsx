import { AlertCircle, AlertTriangle } from 'lucide-react'

import type { FormulaRiskFindingResult } from '@/api/analysis'
import FormulaDisclosure from '@/components/analysis/result/dependency/FormulaDisclosure'
import FormulaRiskImpact from '@/components/analysis/result/formula-risk/FormulaRiskImpact'
import {
  FORMULA_RISK_LEVEL_PRESENTATION,
  FORMULA_RISK_PRESENTATION,
} from '@/components/analysis/result/formula-risk/formulaRiskPresentation'

interface FormulaRiskFindingCardProps {
  finding: FormulaRiskFindingResult
}

const FormulaRiskFindingCard = ({ finding }: FormulaRiskFindingCardProps) => {
  const presentation = FORMULA_RISK_PRESENTATION[finding.kind]
  const isError = finding.severity === 'error'
  const Icon = isError ? AlertCircle : AlertTriangle
  const level = FORMULA_RISK_LEVEL_PRESENTATION[finding.impact?.riskLevel ?? 'low']
  const isHardcoded = finding.kind === 'hardcoded_value'

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
            <div className="flex flex-wrap items-center gap-1.5">
              <span className={`rounded-lg px-2 py-1 text-[11px] font-extrabold ${level.className}`}>
                {level.label}
              </span>
              <span className="rounded-lg bg-slate-100 px-2 py-1 font-mono text-[11px] font-bold text-slate-600">
                {finding.sheetName}!{finding.cell}
              </span>
            </div>
          </div>
          <p className="mt-1 text-sm leading-6 text-slate-600">{finding.message}</p>
          <p className="mt-2 text-xs font-bold text-slate-700">{presentation.action}</p>
          {isHardcoded && finding.observedValue != null && (
            <p className="mt-2 text-xs text-slate-600">
              현재 입력값 <strong className="text-slate-900">{String(finding.observedValue)}</strong>
            </p>
          )}
          <FormulaRiskImpact impact={finding.impact} />
          <FormulaDisclosure
            formula={finding.formula}
            label={isHardcoded ? '주변에서 예상한 수식' : undefined}
          />
        </div>
      </div>
    </article>
  )
}

export default FormulaRiskFindingCard
