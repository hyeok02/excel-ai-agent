import { AlertTriangle, CircleAlert, Info, Lightbulb, Sparkles } from 'lucide-react'

import type {
  InsightCategory,
  InsightReportResult,
  InsightSeverity,
} from '@/api/analysis'
import { cn } from '@/utils/cn'

interface InsightReportSectionProps {
  report: InsightReportResult
}

const CATEGORY_LABELS: Record<InsightCategory, string> = {
  summary: '파일 내용',
  structure: '시트 내용',
  formula: '계산 방식',
  risk: '확인 필요',
}

const SEVERITY_CONFIG: Record<
  InsightSeverity,
  { label: string; className: string; icon: typeof Info }
> = {
  info: {
    label: '현황',
    className: 'bg-brand-50 text-brand-700',
    icon: Info,
  },
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

const InsightReportSection = ({ report }: InsightReportSectionProps) => {
  return (
    <section className="mt-6 overflow-hidden rounded-3xl border border-brand-100 bg-gradient-to-br from-brand-50/80 via-white to-white">
      <div className="border-b border-brand-100/70 p-5 md:p-6">
        <div className="flex items-center gap-2 text-brand-700">
          <Sparkles aria-hidden="true" size={18} />
          <span className="text-xs font-extrabold tracking-[0.12em]">
            CONTENT INSIGHT
          </span>
        </div>
        <h3 className="mt-2 text-lg font-extrabold tracking-tight text-slate-950">
          핵심 현황과 변화
        </h3>
        <p className="mt-3 max-w-4xl text-sm leading-6 text-slate-600">
          {report.overview}
        </p>
      </div>

      <div className="grid gap-3 p-5 md:p-6 lg:grid-cols-2">
        {report.insights.map((insight, index) => {
          const severity = SEVERITY_CONFIG[insight.severity]
          const SeverityIcon = severity.icon

          return (
            <article
              className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm"
              key={`${insight.title}-${index}`}
            >
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
              </div>

              <h4 className="mt-4 text-base font-extrabold text-slate-900">
                {insight.title}
              </h4>
              <p className="mt-2 text-sm leading-6 text-slate-600">
                {insight.description}
              </p>

              <div className="mt-4">
                <p className="text-xs font-extrabold text-slate-500">
                  내용을 확인한 위치
                </p>
                <ul className="mt-2 space-y-1.5">
                  {insight.evidence.map((evidence, evidenceIndex) => (
                    <li
                      className="break-words rounded-xl bg-slate-50 px-3 py-2 text-xs leading-5 text-slate-600"
                      key={`${evidence}-${evidenceIndex}`}
                    >
                      {evidence}
                    </li>
                  ))}
                </ul>
              </div>

              {insight.recommendation && (
                <div className="mt-4 flex items-start gap-2 rounded-xl bg-brand-50/70 p-3 text-sm leading-6 text-slate-700">
                  <Lightbulb
                    aria-hidden="true"
                    className="mt-1 shrink-0 text-brand-600"
                    size={15}
                  />
                  <p>
                    <strong className="mr-1 text-xs text-brand-700">권고</strong>
                    {insight.recommendation}
                  </p>
                </div>
              )}
            </article>
          )
        })}
      </div>

      {report.limitations.length > 0 && (
        <div className="border-t border-brand-100/70 px-5 py-4 md:px-6">
          <p className="text-xs font-extrabold text-slate-500">분석 한계</p>
          <ul className="mt-2 space-y-1 text-xs leading-5 text-slate-500">
            {report.limitations.map((limitation, index) => (
              <li className="flex items-start gap-2" key={`${limitation}-${index}`}>
                <span className="mt-2 size-1 shrink-0 rounded-full bg-slate-400" />
                <span>{limitation}</span>
              </li>
            ))}
          </ul>
        </div>
      )}
    </section>
  )
}

export default InsightReportSection
