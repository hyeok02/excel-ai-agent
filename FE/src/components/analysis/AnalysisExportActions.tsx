import { Braces, Download, FileText } from 'lucide-react'

import type { AnalysisResultDetails } from '@/api/analysis'
import { type AnalysisExportFormat, downloadAnalysisResult } from '@/utils/analysisExport'

interface AnalysisExportActionsProps {
  result: AnalysisResultDetails
}

const EXPORT_OPTIONS: Array<{
  format: AnalysisExportFormat
  icon: typeof Braces
  label: string
}> = [
  { format: 'json', icon: Braces, label: 'JSON' },
  { format: 'yaml', icon: FileText, label: 'YAML' },
]

const AnalysisExportActions = ({ result }: AnalysisExportActionsProps) => {
  return (
    <div className="flex flex-wrap items-center gap-2" aria-label="분석 데이터 내보내기">
      <span className="inline-flex items-center gap-1.5 text-xs font-bold text-slate-500">
        <Download aria-hidden="true" size={14} />
        결과 내보내기
      </span>
      <div className="inline-flex rounded-xl border border-slate-200 bg-white p-1 shadow-sm">
        {EXPORT_OPTIONS.map(({ format, icon: FormatIcon, label }) => (
          <button
            className="inline-flex items-center gap-1.5 rounded-lg px-3 py-1.5 text-xs font-extrabold text-slate-600 transition hover:bg-brand-50 hover:text-brand-700 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-500"
            key={format}
            onClick={() => downloadAnalysisResult(result, format)}
            type="button"
          >
            <FormatIcon aria-hidden="true" size={13} />
            {label}
          </button>
        ))}
      </div>
    </div>
  )
}

export default AnalysisExportActions
