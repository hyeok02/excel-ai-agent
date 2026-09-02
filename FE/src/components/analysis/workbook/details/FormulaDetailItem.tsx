import type { FormulaResult } from '@/api/analysis'
import OriginalLocationButton from '@/components/analysis/workbook/details/OriginalLocationButton'
import { compactFormula, summarizeFormula } from '@/utils/analysis/formulaSummary'

interface FormulaDetailItemProps {
  formula: FormulaResult
  roleLabel: string
  sheetName: string
}

const MAX_VISIBLE_FORMULA_LENGTH = 160
const MAX_VISIBLE_REFERENCE_COUNT = 8

const formatValue = (value: FormulaResult['cachedValue']) => {
  if (value === null || value === '') return null
  if (typeof value === 'boolean') return value ? 'TRUE' : 'FALSE'
  return String(value)
}

const FormulaDetailItem = ({ formula, roleLabel, sheetName }: FormulaDetailItemProps) => {
  const result = formatValue(formula.cachedValue)
  const references = formula.references.slice(0, MAX_VISIBLE_REFERENCE_COUNT)
  const remainingCount = formula.references.length - references.length
  const summary = summarizeFormula(formula.formula)
  const compactedFormula = compactFormula(formula.formula)

  return (
    <div className="rounded-xl bg-slate-50 p-3 text-xs">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div className="flex items-center gap-2">
          <span className="rounded-md bg-brand-50 px-2 py-1 font-extrabold text-brand-700">
            {formula.cell}
          </span>
          <span className="rounded-md bg-white px-2 py-1 font-bold text-slate-500">
            {roleLabel}
          </span>
        </div>
        <OriginalLocationButton location={formula.cell} sheetName={sheetName} />
      </div>

      {result !== null && (
        <p className="mt-2 font-semibold text-slate-700">
          저장된 계산 결과 <b className="text-brand-700">{result}</b>
        </p>
      )}

      {formula.formula.length <= MAX_VISIBLE_FORMULA_LENGTH && (
        <code className="mt-2 block break-all leading-5 text-slate-600">
          {formula.formula}
        </code>
      )}
      {formula.formula.length > MAX_VISIBLE_FORMULA_LENGTH && compactedFormula && (
        <details className="mt-2 overflow-hidden rounded-lg border border-slate-200 bg-white">
          <summary className="flex cursor-pointer list-none items-center justify-between gap-2 px-2 py-1.5 font-bold text-slate-500 marker:hidden">
            <span>기술 상세 · 축약 수식</span>
            <span className="font-semibold text-slate-400">보기</span>
          </summary>
          <div className="border-t border-slate-200 bg-slate-50 p-2">
            <p className="text-[11px] leading-4 text-slate-400">
              원본 수식이 길어 동일한 계산 의미의 TEXTJOIN 수식으로 간결하게 표시했습니다.
            </p>
            <code className="mt-1.5 block overflow-x-auto whitespace-nowrap rounded-lg bg-white px-2 py-1.5 text-slate-600">
              {compactedFormula}
            </code>
          </div>
        </details>
      )}
      {formula.formula.length > MAX_VISIBLE_FORMULA_LENGTH && summary && (
        <p className="mt-2 leading-5 text-slate-500">{summary}</p>
      )}

      <p className="mt-2 break-all text-slate-400">
        참조 셀: {references.length > 0 ? references.join(', ') : '없음'}
        {remainingCount > 0 && ` 외 ${remainingCount.toLocaleString()}곳`}
      </p>
    </div>
  )
}

export default FormulaDetailItem
