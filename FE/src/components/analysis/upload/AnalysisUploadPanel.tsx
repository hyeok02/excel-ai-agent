import { History, TriangleAlert } from 'lucide-react'

import type { AnalysisDepth, AnalysisMode } from '@/api/analysis'
import AnalysisFileDropZone from '@/components/analysis/upload/AnalysisFileDropZone'
import AnalysisOptions from '@/components/analysis/upload/AnalysisOptions'
import type { AnalysisViewStatus } from '@/hooks/analysis/useWorkbookAnalysis'

interface AnalysisUploadPanelProps {
  depth: AnalysisDepth
  errorMessage: string | null
  insightsNeedReanalysis: boolean
  isPending: boolean
  mode: AnalysisMode
  onClearFile: () => void
  onDepthChange: (depth: AnalysisDepth) => void
  onModeChange: (mode: AnalysisMode) => void
  onOpenHistory: () => void
  onSelectFile: (file: File) => void
  onStartAnalysis: () => void
  selectedFile: File | null
  status: AnalysisViewStatus
}

const AnalysisUploadPanel = ({
  depth,
  errorMessage,
  insightsNeedReanalysis,
  isPending,
  mode,
  onClearFile,
  onDepthChange,
  onModeChange,
  onOpenHistory,
  onSelectFile,
  onStartAnalysis,
  selectedFile,
  status,
}: AnalysisUploadPanelProps) => (
  <article className="panel p-5 md:p-7">
    <div className="flex flex-wrap items-start justify-between gap-3">
      <div>
        <h2 className="text-xl font-extrabold tracking-tight text-slate-950">
          분석할 파일을 선택하세요
        </h2>
        <p className="mt-2 text-sm text-slate-500">
          분석 결과는 분석 ID와 함께 저장되며 이후 다시 조회할 수 있어요.
        </p>
      </div>
      <button
        className="inline-flex shrink-0 items-center gap-1.5 rounded-xl border border-slate-200 bg-white px-3 py-2 text-xs font-extrabold text-slate-600 transition hover:border-brand-200 hover:text-brand-700"
        onClick={onOpenHistory}
        type="button"
      >
        <History aria-hidden="true" size={14} /> 분석한 파일 불러오기
      </button>
    </div>

    <AnalysisOptions
      depth={depth}
      insightsNeedReanalysis={insightsNeedReanalysis}
      isPending={isPending}
      mode={mode}
      onDepthChange={onDepthChange}
      onModeChange={onModeChange}
    />
    <AnalysisFileDropZone
      isPending={isPending}
      onClearFile={onClearFile}
      onSelectFile={onSelectFile}
      onStartAnalysis={onStartAnalysis}
      selectedFile={selectedFile}
      status={status}
    />

    {errorMessage && (
      <div
        className="mt-4 flex items-start gap-3 rounded-2xl border border-red-100 bg-red-50 p-4 text-sm text-red-700"
        role="alert"
      >
        <TriangleAlert aria-hidden="true" className="mt-0.5 shrink-0" size={17} />
        <p>{errorMessage}</p>
      </div>
    )}
  </article>
)

export default AnalysisUploadPanel
