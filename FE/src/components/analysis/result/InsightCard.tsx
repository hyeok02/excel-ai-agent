import { AlertTriangle, CircleAlert, Info, ShieldCheck } from 'lucide-react'

import type {
  InsightCategory,
  InsightResult,
  InsightSeverity,
} from '@/api/analysis/insightTypes'
import InsightCardBody from '@/components/analysis/result/InsightCardBody'
import { insightValidationLabel } from '@/components/analysis/result/insightReportPresentation'
import { cn } from '@/utils/cn'

const CATEGORY_LABELS: Record<InsightCategory, string> = {
  metric: '핵심 지표',
  trend: '추세',
  summary: '파일 내용',
  structure: '시트 내용',
  formula: '계산 방식',
  risk: '이상징후',
}

const SEVERITY_CONFIG: Record<
  InsightSeverity,
  { label: string; className: string; icon: typeof Info }
> = {
  info: { label: '현황', className: 'bg-brand-50 text-brand-700', icon: Info },
  warning: {
    label: '확인 필요',
    className: 'bg-amber-50 text-amber-700',
    icon: AlertTriangle,
  },
  critical: {
    label: '우선 검토',
    className: 'bg-red-50 text-red-700',
    icon: CircleAlert,
  },
}

interface InsightCardProps {
  insight: InsightResult
}

const InsightCard = ({ insight }: InsightCardProps) => {
  const severity = SEVERITY_CONFIG[insight.severity]
  const SeverityIcon = severity.icon
  const isVerified = insight.validationStatus === 'verified'

  return (
    <article className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
      <div className="flex flex-wrap items-center gap-2">
        {insight.severity !== 'info' && (
          <span
            className={cn(
              'inline-flex items-center gap-1.5 rounded-full px-2.5 py-1 text-xs font-bold',
              severity.className,
            )}
          >
            <SeverityIcon aria-hidden="true" size={13} />
            {severity.label}
          </span>
        )}
        <span className="rounded-full bg-slate-100 px-2.5 py-1 text-xs font-bold text-slate-500">
          {CATEGORY_LABELS[insight.category]}
        </span>
        <span
          className={cn(
            'ml-auto inline-flex items-center gap-1 rounded-full px-2.5 py-1 text-xs font-bold',
            insight.validationStatus === null
              ? 'bg-slate-100 text-slate-500'
              : isVerified
                ? 'bg-emerald-50 text-emerald-700'
                : 'bg-amber-50 text-amber-700',
          )}
        >
          {isVerified ? (
            <ShieldCheck aria-hidden="true" size={13} />
          ) : (
            <CircleAlert aria-hidden="true" size={13} />
          )}
          {insightValidationLabel(insight.validationStatus)}
        </span>
      </div>

      <h4 className="mt-4 text-base font-extrabold text-slate-900">{insight.title}</h4>
      <InsightCardBody insight={insight} />
    </article>
  )
}

export default InsightCard
