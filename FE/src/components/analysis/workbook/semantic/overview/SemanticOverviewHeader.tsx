import { Network } from 'lucide-react'

const SemanticOverviewHeader = () => (
  <div className="relative overflow-hidden bg-gradient-to-br from-[#165fd7] via-brand-600 to-cyan-500 p-5 text-white md:p-6">
    <span className="pointer-events-none absolute -right-16 -top-24 size-60 rounded-full border border-white/15" />
    <span className="pointer-events-none absolute -bottom-20 right-28 size-44 rounded-full bg-white/5" />
    <div className="relative flex flex-wrap items-start justify-between gap-5">
      <div>
        <div className="flex items-center gap-2 text-blue-100">
          <Network aria-hidden="true" size={18} />
          <span className="text-xs font-extrabold tracking-[0.16em]">
            RULE-BASED SEMANTIC ANALYSIS
          </span>
        </div>
        <h3 className="mt-2 text-lg font-extrabold md:text-xl">워크북 의미 구조 분석</h3>
        <p className="mt-1 max-w-2xl text-sm leading-6 text-blue-100">
          셀 값·수식·서식과 탐지 규칙을 기반으로 시트와 영역의 역할, 분석 포함 여부와 판단
          근거를 분류했어요.
        </p>
      </div>
      <span className="rounded-xl border border-white/20 bg-white/10 px-3 py-2 text-xs font-bold text-blue-50 backdrop-blur">
        공통 구조 분석 · 규칙 기반
      </span>
    </div>
  </div>
)

export default SemanticOverviewHeader
