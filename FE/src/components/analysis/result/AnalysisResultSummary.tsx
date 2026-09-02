import type { WorkbookResult } from '@/api/analysis'
import { getWorkbookSummaryItems } from '@/components/analysis/result/analysisResultPresentation'

interface AnalysisResultSummaryProps {
  workbook: WorkbookResult
}

const AnalysisResultSummary = ({ workbook }: AnalysisResultSummaryProps) => {
  return (
    <div className="mt-6 grid gap-3 sm:grid-cols-2 xl:grid-cols-5">
      {getWorkbookSummaryItems(workbook).map(([label, value]) => (
        <div className="rounded-2xl bg-slate-50 p-4" key={label}>
          <p className="text-xs font-semibold text-slate-400">{label}</p>
          <p className="mt-2 text-2xl font-extrabold tracking-tight text-slate-900">
            {value.toLocaleString()}
          </p>
        </div>
      ))}
    </div>
  )
}

export default AnalysisResultSummary
