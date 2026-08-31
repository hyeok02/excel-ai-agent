import { AlertTriangle, ShieldCheck, Sparkles } from 'lucide-react'

import type { InsightReportResult } from '@/api/analysis'
import InsightCard from '@/components/analysis/result/InsightCard'

interface InsightReportSectionProps {
  report: InsightReportResult
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
        {report.hasIncompleteData && (
          <div className="mt-4 flex items-start gap-2 rounded-xl border border-amber-200 bg-amber-50 p-3 text-sm leading-6 text-amber-900">
            <AlertTriangle aria-hidden="true" className="mt-0.5 shrink-0" size={16} />
            <p>
              일부 상세 내용이 저장되지 않았습니다. AI와 백엔드 서비스를 최신 코드로
              재시작한 뒤 같은 파일을 다시 분석해 주세요.
            </p>
          </div>
        )}
      </div>

      {report.validation && (
        <div className="grid gap-3 border-b border-brand-100/70 p-5 sm:grid-cols-3 md:p-6">
          <ValidationMetric label="검증 통과" value={report.validation.verifiedCount} />
          <ValidationMetric label="근거 확인 필요" value={report.validation.limitedCount} />
          <ValidationMetric label="내용 누락 제외" value={report.validation.blockedCount} />
        </div>
      )}

      <div className="grid gap-3 p-5 md:p-6 lg:grid-cols-2">
        {report.insights.map((insight, index) => (
          <InsightCard insight={insight} key={`${insight.title}-${index}`} />
        ))}
        {report.insights.length === 0 && (
          <div className="rounded-2xl border border-amber-200 bg-amber-50 p-5 lg:col-span-2">
            <p className="text-sm font-extrabold text-amber-900">
              근거 검증을 통과한 인사이트가 없습니다
            </p>
            <p className="mt-1 text-sm leading-6 text-amber-800">
              근거가 확인되지 않은 주장은 표시하지 않았습니다. 아래 분석 한계와 원본
              위치를 확인해 주세요.
            </p>
          </div>
        )}
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

const ValidationMetric = ({ label, value }: { label: string; value: number }) => (
  <div className="rounded-xl bg-white/80 px-4 py-3 text-sm shadow-sm">
    <p className="text-xs font-bold text-slate-500">{label}</p>
    <p className="mt-1 flex items-center gap-1.5 text-lg font-extrabold text-slate-900">
      <ShieldCheck aria-hidden="true" className="text-brand-600" size={16} />
      {value}건
    </p>
  </div>
)

export default InsightReportSection
