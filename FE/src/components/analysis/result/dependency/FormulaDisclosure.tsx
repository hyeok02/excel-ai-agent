import { Check, Copy } from 'lucide-react'
import { useState } from 'react'

import { compactFormula, summarizeFormula } from '@/utils/analysis/formulaSummary'

interface FormulaDisclosureProps {
  formula: string
  label?: string
}

const MAX_VISIBLE_FORMULA_LENGTH = 160

const FormulaDisclosure = ({ formula, label = 'Excel 수식 원문' }: FormulaDisclosureProps) => {
  const [copied, setCopied] = useState(false)
  const summary = summarizeFormula(formula)
  const compactedFormula = compactFormula(formula)

  if (formula.length > MAX_VISIBLE_FORMULA_LENGTH) {
    if (!compactedFormula && !summary) return null
    return (
      <details className="mt-3 overflow-hidden rounded-xl border border-slate-200 bg-white">
        <summary className="flex cursor-pointer list-none items-center justify-between gap-3 px-3 py-2 text-[11px] font-bold text-slate-500 marker:hidden">
          <span>기술 상세 · {label === 'Excel 수식 원문' ? '축약 수식' : label}</span>
          <span className="shrink-0 font-semibold text-slate-400">보기</span>
        </summary>
        <div className="border-t border-slate-200 bg-slate-50 p-3">
          <p className="text-[11px] leading-4 text-slate-500">
            원본 수식이 길어 동일한 계산 의미의 TEXTJOIN 수식으로 간결하게 표시했습니다.
          </p>
          {compactedFormula && (
            <code className="mt-2 block overflow-x-auto whitespace-nowrap rounded-lg bg-white px-3 py-2 font-mono text-[11px] text-slate-700">
              {compactedFormula}
            </code>
          )}
          {summary && <p className="mt-2 text-xs leading-5 text-slate-500">{summary}</p>}
        </div>
      </details>
    )
  }

  const copyFormula = async () => {
    try {
      await navigator.clipboard.writeText(formula)
      setCopied(true)
      window.setTimeout(() => setCopied(false), 1500)
    } catch {
      setCopied(false)
    }
  }

  return (
    <details className="mt-3 overflow-hidden rounded-xl border border-slate-200 bg-white">
      <summary className="flex cursor-pointer list-none items-center justify-between gap-3 px-3 py-2 text-[11px] font-bold text-slate-500 marker:hidden">
        <span>기술 상세 · {label}</span>
        <span className="shrink-0 font-semibold text-slate-400">보기</span>
      </summary>
      <div className="border-t border-slate-200 bg-slate-950 p-3">
        <div className="mb-2 flex items-center justify-between gap-3">
          <span className="text-[10px] font-bold tracking-wide text-slate-400">
            EXCEL FORMULA
          </span>
          <button
            className="inline-flex items-center gap-1 rounded-lg bg-white/10 px-2 py-1 text-[10px] font-bold text-slate-200 hover:bg-white/15"
            onClick={() => void copyFormula()}
            type="button"
          >
            {copied ? (
              <Check aria-hidden="true" size={11} />
            ) : (
              <Copy aria-hidden="true" size={11} />
            )}
            {copied ? '복사됨' : '수식 복사'}
          </button>
        </div>
        <div className="max-h-44 overflow-auto rounded-lg bg-black/20 p-3">
          <code className="block min-w-max whitespace-pre font-mono text-[11px] leading-5 text-slate-200">
            {formula}
          </code>
        </div>
        <p className="mt-2 text-[10px] leading-4 text-slate-400">
          원본 검증이 필요할 때만 확인하는 개발자용 정보입니다.
        </p>
      </div>
    </details>
  )
}

export default FormulaDisclosure
