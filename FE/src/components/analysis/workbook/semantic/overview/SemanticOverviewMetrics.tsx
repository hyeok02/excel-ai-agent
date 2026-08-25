import { Layers3, ScanSearch, ShieldCheck } from 'lucide-react'

interface SemanticOverviewMetricsProps {
  classifiedRegionCount: number
  excludedSheetCount: number
  includedSheetCount: number
}

const SemanticOverviewMetrics = ({
  classifiedRegionCount,
  excludedSheetCount,
  includedSheetCount,
}: SemanticOverviewMetricsProps) => {
  const metrics = [
    {
      label: '분석 대상 시트',
      value: includedSheetCount,
      helper: '업무 의미 분석 포함',
      icon: Layers3,
    },
    {
      label: '의미 분류 영역',
      value: classifiedRegionCount,
      helper: '역할과 근거 생성',
      icon: ScanSearch,
    },
    {
      label: '제외 시트',
      value: excludedSheetCount,
      helper: '제외 사유 기록',
      icon: ShieldCheck,
    },
  ]

  return (
    <div className="grid gap-3 border-b border-slate-100 p-5 sm:grid-cols-3 md:p-6">
      {metrics.map(({ helper, icon: Icon, label, value }) => (
        <article className="rounded-2xl bg-slate-50 p-4" key={label}>
          <div className="flex items-center justify-between gap-3">
            <p className="text-xs font-bold text-slate-500">{label}</p>
            <span className="grid size-8 place-items-center rounded-xl bg-white text-brand-600 shadow-sm">
              <Icon aria-hidden="true" size={15} />
            </span>
          </div>
          <p className="mt-3 text-2xl font-extrabold tracking-tight text-slate-950">
            {value.toLocaleString()}
          </p>
          <p className="mt-1 text-[11px] text-slate-400">{helper}</p>
        </article>
      ))}
    </div>
  )
}

export default SemanticOverviewMetrics
