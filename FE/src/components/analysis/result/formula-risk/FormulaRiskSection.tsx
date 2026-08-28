import { CheckCircle2, ShieldAlert } from 'lucide-react'
import { useState } from 'react'

import type { FormulaRiskSummaryResult } from '@/api/analysis'
import FormulaRiskFindingCard from '@/components/analysis/result/formula-risk/FormulaRiskFindingCard'

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
    <section className="mt-6 overflow-hidden rounded-3xl border border-amber-200 bg-amber-50/30">
      <header className="flex flex-wrap items-start justify-between gap-3 border-b border-amber-100 p-5">
        <div className="flex items-start gap-3">
          <span className="grid size-10 place-items-center rounded-xl bg-amber-100 text-amber-700">
            <ShieldAlert aria-hidden="true" size={19} />
          </span>
          <div>
            <h3 className="font-extrabold text-slate-950">수식 위험 점검</h3>
            <p className="mt-1 text-sm text-slate-600">
              계산 오류 또는 유지보수 문제로 이어질 수 있는 수식 {summary.totalCount}건입니다.
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
            <span className="rounded-full bg-amber-100 px-3 py-1.5 text-amber-700">
              주의 {summary.warningCount}
            </span>
          )}
        </div>
      </header>

      <div className="grid gap-3 p-5 lg:grid-cols-2">
        {findings.map((finding, index) => (
          <FormulaRiskFindingCard
            finding={finding}
            key={`${finding.sheetName}-${finding.cell}-${finding.kind}-${index}`}
          />
        ))}
      </div>

      {summary.findings.length > VISIBLE_FINDINGS && (
        <button
          className="w-full border-t border-amber-100 px-5 py-3 text-sm font-extrabold text-brand-700 hover:bg-white/60"
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
