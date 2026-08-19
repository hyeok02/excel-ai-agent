import { Sigma } from 'lucide-react'

import type { FormulaResult } from '@/api/analysis'

interface SheetFormulaDetailsProps {
  formulas: FormulaResult[]
}

const SheetFormulaDetails = ({ formulas }: SheetFormulaDetailsProps) => {
  return (
    <section className="rounded-2xl bg-slate-50/80 p-4">
      <div className="flex items-center gap-2">
        <Sigma aria-hidden="true" className="text-brand-600" size={16} />
        <h4 className="text-xs font-extrabold tracking-wide text-slate-700">
          수식과 셀 참조 관계
        </h4>
      </div>

      {formulas.length > 0 ? (
        <div className="mt-3 max-h-96 space-y-2 overflow-auto pr-1">
          {formulas.map((formula) => (
            <div className="rounded-xl border border-slate-200 bg-white p-3 text-xs" key={formula.cell}>
              <div className="flex items-start gap-2">
                <span className="shrink-0 rounded-md bg-brand-50 px-2 py-1 font-extrabold text-brand-700">
                  {formula.cell}
                </span>
                <code className="break-all pt-1 leading-5 text-slate-600">
                  {formula.formula}
                </code>
              </div>
              <p className="mt-2 break-all text-slate-400">
                참조: {formula.references.length > 0 ? formula.references.join(', ') : '없음'}
              </p>
            </div>
          ))}
        </div>
      ) : (
        <p className="mt-3 rounded-xl bg-white p-4 text-xs text-slate-400">
          분석할 수식이 없습니다.
        </p>
      )}
    </section>
  )
}

export default SheetFormulaDetails
