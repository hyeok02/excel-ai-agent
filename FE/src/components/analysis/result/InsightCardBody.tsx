import { Lightbulb } from 'lucide-react'

import type { InsightResult } from '@/api/analysis/insightTypes'
import { cn } from '@/utils/cn'

const InsightCardBody = ({ insight }: { insight: InsightResult }) => (
  <>
    <Detail
      label="확인된 사실"
      text={insight.fact || '확인된 사실의 상세 내용이 저장되지 않았습니다.'}
    />
    {insight.cause && <Detail bordered label="확인된 원인" text={insight.cause} />}
    {insight.impact && <Detail impact label="검토 포인트" text={insight.impact} />}
    <div className="mt-4">
      <p className="text-xs font-extrabold text-slate-500">내용을 확인한 위치</p>
      <ul className="mt-2 space-y-1.5">
        {insight.evidence.map((evidence, index) => (
          <li
            className="break-words rounded-xl bg-slate-50 px-3 py-2 text-xs leading-5 text-slate-600"
            key={`${evidence}-${index}`}
          >
            {evidence}
          </li>
        ))}
      </ul>
    </div>
    {insight.validationReasons.length > 0 && (
      <p className="mt-3 text-xs leading-5 text-amber-700">
        {insight.validationReasons.join(' · ')}
      </p>
    )}
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
  </>
)

const Detail = ({
  bordered = false,
  impact = false,
  label,
  text,
}: {
  bordered?: boolean
  impact?: boolean
  label: string
  text: string
}) => (
  <div
    className={cn(
      'mt-3 rounded-xl p-3',
      impact ? 'bg-amber-50/70' : bordered ? 'border border-slate-200' : 'bg-slate-50',
    )}
  >
    <p
      className={cn(
        'text-xs font-extrabold',
        impact ? 'text-amber-700' : 'text-slate-500',
      )}
    >
      {label}
    </p>
    <p className="mt-1 text-sm leading-6 text-slate-700">{text}</p>
  </div>
)

export default InsightCardBody
