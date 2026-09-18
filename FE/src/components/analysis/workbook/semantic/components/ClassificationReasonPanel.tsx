import { BadgeInfo, MapPin } from 'lucide-react'

import type { AnalysisInclusion, SemanticReason } from '@/api/analysis'

export interface ClassificationReasonPanelProps {
  reasons: SemanticReason[]
  analysisInclusion?: AnalysisInclusion | null
  title?: string
}

const ClassificationReasonPanel = ({
  reasons,
  analysisInclusion,
  title = '판단 근거',
}: ClassificationReasonPanelProps) => {
  return (
    <div className="rounded-xl border border-slate-200 bg-slate-50/70 p-3.5">
      <div className="flex items-center gap-2 text-xs font-extrabold text-slate-700">
        <BadgeInfo aria-hidden="true" className="text-brand-600" size={14} />
        {title}
      </div>

      {analysisInclusion && (
        <div className="mt-3 rounded-lg bg-white px-3 py-2.5">
          <p className="text-[10px] font-extrabold tracking-wide text-slate-400">
            분석 정책 · {analysisInclusion.reasonCode}
          </p>
          <p className="mt-1 text-xs leading-5 text-slate-600">
            {analysisInclusion.reason}
          </p>
        </div>
      )}

      {reasons.length > 0 ? (
        <ul className="mt-3 space-y-2">
          {reasons.map((reason, index) => (
            <li
              className="rounded-lg bg-white px-3 py-2.5"
              key={`${reason.code}-${index}`}
            >
              <div className="flex flex-wrap items-start justify-between gap-2">
                <p className="text-xs font-semibold leading-5 text-slate-600">
                  {reason.message}
                </p>
                <span className="rounded-md bg-slate-100 px-2 py-1 text-[9px] font-bold text-slate-400">
                  {reason.code}
                </span>
              </div>
              {reason.evidenceCells.length > 0 && (
                <div className="mt-2 flex flex-wrap items-center gap-1.5">
                  <MapPin aria-hidden="true" className="text-slate-300" size={11} />
                  {reason.evidenceCells.map((cell) => (
                    <code
                      className="rounded-md bg-brand-50 px-1.5 py-1 text-[10px] font-bold text-brand-700"
                      key={cell}
                    >
                      {cell}
                    </code>
                  ))}
                </div>
              )}
            </li>
          ))}
        </ul>
      ) : (
        <p className="mt-3 text-xs text-slate-400">제공된 판단 근거가 없습니다.</p>
      )}
    </div>
  )
}

export default ClassificationReasonPanel
