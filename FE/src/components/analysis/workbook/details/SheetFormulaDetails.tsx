import { Calculator, ExternalLink, Search, Sigma, Type } from 'lucide-react'

import type { FormulaResult } from '@/api/analysis'
import FormulaDetailItem from '@/components/analysis/workbook/details/FormulaDetailItem'

interface SheetFormulaDetailsProps {
  formulas: FormulaResult[]
  sheetName: string
}

const roleDetails = {
  calculation: {
    label: '계산 수식',
    description: '합계·비율·조건 계산 등 실제 값을 계산해요.',
    icon: Calculator,
  },
  lookup: {
    label: '조회·참조 수식',
    description: '다른 셀이나 표에서 필요한 값을 찾아와요.',
    icon: Search,
  },
  presentation: {
    label: '표시·문구 수식',
    description: '계산 결과를 화면에 보여줄 문구나 형식으로 바꿔요.',
    icon: Type,
  },
  external: {
    label: '외부 기능 수식',
    description: '추가 기능이나 다른 파일·서비스에 의존해요.',
    icon: ExternalLink,
  },
} as const

const SheetFormulaDetails = ({ formulas, sheetName }: SheetFormulaDetailsProps) => {
  if (formulas.length === 0) return null

  const roleCounts = Object.keys(roleDetails).map((role) => ({
    role: role as keyof typeof roleDetails,
    count: formulas.filter((formula) => (formula.role ?? 'calculation') === role).length,
  }))

  return (
    <section className="rounded-2xl bg-slate-50/80 p-4">
      <div className="flex items-center gap-2">
        <Sigma aria-hidden="true" className="text-brand-600" size={16} />
        <h4 className="text-xs font-extrabold tracking-wide text-slate-700">
          수식 역할과 계산 결과
        </h4>
      </div>

      <div className="mt-3 grid gap-2 sm:grid-cols-2">
        {roleCounts
          .filter(({ count }) => count > 0)
          .map(({ role, count }) => {
            const details = roleDetails[role]
            const Icon = details.icon
            return (
              <div className="rounded-xl border border-slate-200 bg-white p-3" key={role}>
                <div className="flex items-center justify-between gap-2">
                  <span className="flex items-center gap-2 text-xs font-extrabold text-slate-700">
                    <Icon aria-hidden="true" className="text-brand-600" size={14} />
                    {details.label}
                  </span>
                  <b className="text-xs text-brand-700">{count.toLocaleString()}개</b>
                </div>
                <p className="mt-1.5 text-[11px] leading-5 text-slate-400">
                  {details.description}
                </p>
              </div>
            )
          })}
      </div>

      <details className="mt-3 rounded-xl border border-slate-200 bg-white">
        <summary className="cursor-pointer list-none px-4 py-3 text-xs font-extrabold text-slate-700 marker:hidden">
          수식 상세 보기
          <span className="ml-2 font-medium text-slate-400">
            대표 {Math.min(formulas.length, 40)}개
          </span>
        </summary>
        <div className="max-h-[30rem] space-y-2 overflow-auto border-t border-slate-100 p-3">
          {formulas.slice(0, 40).map((formula) => {
            const role = formula.role ?? 'calculation'
            return (
              <FormulaDetailItem
                formula={formula}
                key={formula.cell}
                roleLabel={roleDetails[role].label}
                sheetName={sheetName}
              />
            )
          })}
          {formulas.length > 40 && (
            <p className="py-2 text-center text-[11px] text-slate-400">
              화면에는 대표 40개를 표시하고 전체 수식은 내보내기 파일에 포함합니다.
            </p>
          )}
        </div>
      </details>
    </section>
  )
}

export default SheetFormulaDetails
