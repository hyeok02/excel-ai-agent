import { CheckCircle2, ChevronDown, ShieldAlert } from 'lucide-react'
import { useState } from 'react'

import type { FormulaRiskSummaryResult } from '@/api/analysis'
import ResponsiveCardColumns from '@/components/analysis/common/ResponsiveCardColumns'
import FormulaRiskFindingCard from '@/components/analysis/result/formula-risk/FormulaRiskFindingCard'
import FormulaRiskOverview from '@/components/analysis/result/formula-risk/FormulaRiskOverview'

interface FormulaRiskSectionProps {
  summary: FormulaRiskSummaryResult
}

const VISIBLE_FINDINGS = 6

const FormulaRiskSection = ({ summary }: FormulaRiskSectionProps) => {
  const [expanded, setExpanded] = useState(false)
  // 주변과 다른 수식과 직접 입력된 값은 의도한 경우가 많아 따로 접어 둔다.
  const checked = summary.findings.filter((item) => item.severity !== 'info')
  const noted = summary.findings.filter((item) => item.severity === 'info')
  const visible = expanded ? checked : checked.slice(0, VISIBLE_FINDINGS)

  if (checked.length === 0 && noted.length === 0) {
    return (
      <section className="mt-6 flex items-center gap-3 rounded-2xl border border-emerald-200 bg-emerald-50/70 p-4">
        <CheckCircle2 aria-hidden="true" className="text-emerald-600" size={20} />
        <div>
          <h3 className="text-sm font-extrabold text-slate-900">수식 위험 점검 완료</h3>
          <p className="mt-0.5 text-xs text-slate-600">
            계산 오류로 남은 셀, 깨진 참조, 외부 파일 연결이 없습니다.
          </p>
        </div>
      </section>
    )
  }

  return (
    <section className="mt-6 overflow-hidden rounded-3xl border border-slate-200 bg-white shadow-sm">
      <header className="flex flex-wrap items-start justify-between gap-3 border-b border-slate-100 p-5">
        <div className="flex items-start gap-3">
          <span className="grid size-10 place-items-center rounded-xl bg-red-50 text-red-600">
            <ShieldAlert aria-hidden="true" size={19} />
          </span>
          <div>
            <h3 className="font-extrabold text-slate-950">수식 위험 점검</h3>
            <p className="mt-1 text-sm text-slate-600">
              계산이 이미 실패한 셀과, 파일을 옮기거나 시트를 바꾸면 끊어질 참조를
              찾았습니다.
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
              확인 필요 {summary.warningCount}
            </span>
          )}
        </div>
      </header>

      <FormulaRiskOverview summary={summary} />

      {checked.length > 0 && (
        <>
          <ResponsiveCardColumns
            className="p-5"
            getKey={(finding, index) =>
              `${finding.sheetName}-${finding.cell}-${finding.kind}-${index}`
            }
            items={visible}
            renderItem={(finding) => <FormulaRiskFindingCard finding={finding} />}
          />
          {checked.length > VISIBLE_FINDINGS && (
            <button
              className="w-full border-t border-slate-100 px-5 py-3 text-sm font-extrabold text-brand-700 transition hover:bg-slate-50"
              onClick={() => setExpanded((value) => !value)}
              type="button"
            >
              {expanded ? '접기' : `나머지 ${checked.length - VISIBLE_FINDINGS}건 보기`}
            </button>
          )}
        </>
      )}

      {noted.length > 0 && (
        <details className="group border-t border-slate-100">
          <summary className="flex cursor-pointer list-none items-center justify-between p-5 text-sm font-extrabold text-slate-600">
            <span>
              참고 항목 {noted.length}건
              <span className="ml-2 text-xs font-semibold text-slate-400">
                주변과 다른 수식, 직접 입력된 값 · 의도한 경우가 많습니다
              </span>
            </span>
            <ChevronDown className="transition group-open:rotate-180" size={16} />
          </summary>
          <ResponsiveCardColumns
            className="px-5 pb-5"
            getKey={(finding, index) =>
              `${finding.sheetName}-${finding.cell}-${finding.kind}-${index}`
            }
            items={noted.slice(0, 20)}
            renderItem={(finding) => <FormulaRiskFindingCard finding={finding} />}
          />
        </details>
      )}
    </section>
  )
}

export default FormulaRiskSection
