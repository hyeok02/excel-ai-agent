import { ChevronDown, SearchCheck } from 'lucide-react'
import { type ReactNode, useState } from 'react'

const AdvancedAnalysisSection = ({ children }: { children: ReactNode }) => {
  const [expanded, setExpanded] = useState(false)

  return (
    <section className="mt-6 overflow-hidden rounded-3xl border border-slate-200 bg-slate-50/70">
      <button
        aria-expanded={expanded}
        className="flex w-full items-center justify-between gap-4 p-5 text-left transition hover:bg-white md:p-6"
        onClick={() => setExpanded((current) => !current)}
        type="button"
      >
        <span className="flex min-w-0 items-center gap-3">
          <span className="grid size-11 shrink-0 place-items-center rounded-2xl bg-white text-brand-600 shadow-sm ring-1 ring-slate-200">
            <SearchCheck aria-hidden="true" size={20} />
          </span>
          <span>
            <span className="block text-base font-extrabold text-slate-900">
              {expanded ? '상세 분석 접기' : '상세 분석 보기'}
            </span>
            <span className="mt-1 block text-xs leading-5 text-slate-500">
              워크북 구조, 수식 위험과 시트별 원본 내용을 확인할 수 있어요.
            </span>
          </span>
        </span>
        <ChevronDown
          aria-hidden="true"
          className={`shrink-0 text-slate-400 transition-transform ${expanded ? 'rotate-180' : ''}`}
          size={20}
        />
      </button>

      {expanded && (
        <div className="border-t border-slate-200 bg-white p-4 md:p-5">{children}</div>
      )}
    </section>
  )
}

export default AdvancedAnalysisSection
