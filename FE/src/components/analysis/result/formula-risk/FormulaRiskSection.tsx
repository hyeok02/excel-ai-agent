import { CheckCircle2, ShieldAlert } from 'lucide-react'
import { useState } from 'react'

import type { FormulaRiskSummaryResult } from '@/api/analysis'
import FormulaRiskFindingCard from '@/components/analysis/result/formula-risk/FormulaRiskFindingCard'
import FormulaRiskOverview from '@/components/analysis/result/formula-risk/FormulaRiskOverview'

interface FormulaRiskSectionProps {
  summary: FormulaRiskSummaryResult
}

const VISIBLE_FINDINGS = 3

const FormulaRiskSection = ({ summary }: FormulaRiskSectionProps) => {
  const [expanded, setExpanded] = useState(false)
  const hasRisks = summary.totalCount > 0
  const findings = expanded ? summary.findings : summary.findings.slice(0, VISIBLE_FINDINGS)
  const hiddenCount = summary.findings.length - findings.length

  if (!hasRisks) {
    return (
      <section className="mt-6 flex items-center gap-3 rounded-2xl border border-emerald-200 bg-emerald-50/70 p-4">
        <CheckCircle2 aria-hidden="true" className="text-emerald-600" size={20} />
        <div>
          <h3 className="text-sm font-extrabold text-slate-900">수식 위험 점검 완료</h3>
          <p className="mt-0.5 text-xs text-slate-600">
            깨진 참조, 외부 파일 연결, 추적이 어려운 동적 참조가 없습니다.
          </p>
        </div>
      </section>
    )
  }

  return (
    <section className="mt-6 overflow-hidden rounded-3xl border border-blue-200/80 bg-gradient-to-br from-blue-50/80 via-white to-indigo-50/70 shadow-[0_18px_50px_-38px_rgba(37,99,235,0.45)]">
      <header className="flex flex-wrap items-start justify-between gap-3 border-b border-blue-100 bg-white/45 p-5">
        <div className="flex items-start gap-3">
          <span className="grid size-10 place-items-center rounded-xl bg-gradient-to-br from-blue-100 to-indigo-100 text-brand-700 ring-1 ring-blue-200/80">
            <ShieldAlert aria-hidden="true" size={19} />
          </span>
          <div>
            <h3 className="font-extrabold text-slate-950">수식 오류·영향 점검</h3>
            <p className="mt-1 text-sm text-slate-600">
              주변과 다른 수식과 직접 입력된 값을 찾고, 결과가 어디까지 영향을 받는지 계산했습니다.
            </p>
          </div>
        </div>
        <div className="flex gap-2 text-xs font-bold">
          {summary.errorCount > 0 && (
            <span className="rounded-full bg-red-100 px-3 py-1.5 text-red-700">
              오류 {summary.errorCount}
            </span>
          )}
          {summary.warningCount > 0 && (
            <span className="rounded-full bg-blue-100 px-3 py-1.5 text-blue-700 ring-1 ring-blue-200/70">
              주의 {summary.warningCount}
            </span>
          )}
        </div>
      </header>

      <FormulaRiskOverview summary={summary} />

      <div className="grid items-start gap-3 p-5 lg:grid-cols-2">
        {findings.map((finding, index) => (
          <FormulaRiskFindingCard
            finding={finding}
            key={`${finding.sheetName}-${finding.cell}-${finding.kind}-${index}`}
          />
        ))}
      </div>

      {summary.findings.length > VISIBLE_FINDINGS && (
        <button
          className="w-full border-t border-blue-100 bg-white/35 px-5 py-3 text-sm font-extrabold text-brand-700 transition hover:bg-blue-50/70"
          onClick={() => setExpanded((value) => !value)}
          type="button"
        >
          {expanded ? '위험 항목 접기' : `나머지 ${hiddenCount}건 보기`}
        </button>
      )}
    </section>
  )
}

export default FormulaRiskSection
