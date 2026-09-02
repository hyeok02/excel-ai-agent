import { CalendarClock, CheckCircle2 } from 'lucide-react'

import type { AnalysisMode, AnalysisResultDetails } from '@/api/analysis'
import AnalysisExportActions from '@/components/analysis/result/AnalysisExportActions'
import { MODE_PRESENTATION } from '@/components/analysis/result/analysisResultPresentation'

interface AnalysisResultHeaderProps {
  mode: AnalysisMode
  result: AnalysisResultDetails
}

const AnalysisResultHeader = ({ mode, result }: AnalysisResultHeaderProps) => {
  return (
    <div className="flex flex-wrap items-start justify-between gap-4">
      <div>
        <div className="flex items-center gap-2 text-emerald-600">
          <CheckCircle2 aria-hidden="true" size={18} />
          <span className="text-xs font-extrabold tracking-wide">
            {MODE_PRESENTATION[mode].completion}
          </span>
        </div>
        <h2 className="mt-2 text-xl font-extrabold tracking-tight text-slate-950">
          {result.workbook.filename}
        </h2>
        <p className="mt-1 text-sm text-slate-500">분석 ID {result.analysisId}</p>
      </div>
      <div className="flex w-full flex-wrap items-center gap-2 sm:w-auto sm:justify-end">
        <time
          className="inline-flex h-10 items-center gap-2 rounded-xl bg-slate-50 px-3 text-xs font-semibold text-slate-500"
          dateTime={result.createdAt}
        >
          <CalendarClock aria-hidden="true" size={15} />
          {new Date(result.createdAt).toLocaleString('ko-KR')}
        </time>
        <AnalysisExportActions result={result} />
      </div>
    </div>
  )
}

export default AnalysisResultHeader
