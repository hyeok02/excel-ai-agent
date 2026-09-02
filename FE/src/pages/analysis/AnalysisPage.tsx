import { useState } from 'react'

import AnalysisFeedback from '@/components/analysis/common/AnalysisFeedback'
import AnalysisHeader from '@/components/analysis/common/AnalysisHeader'
import AnalysisResultSection from '@/components/analysis/result/AnalysisResultSection'
import AnalysisFlowPanel from '@/components/analysis/upload/AnalysisFlowPanel'
import AnalysisHistoryDialog from '@/components/analysis/upload/AnalysisHistoryDialog'
import AnalysisUploadPanel from '@/components/analysis/upload/AnalysisUploadPanel'
import { useWorkbookAnalysis } from '@/hooks/analysis/useWorkbookAnalysis'

const AnalysisPage = () => {
  const {
    activeAnalysisId,
    activeStep,
    analysisResult,
    analysisResultMode,
    changeDepth,
    changeMode,
    clearFile,
    depth,
    errorMessage,
    feedback,
    isPending,
    mode,
    openAnalysis,
    processingStatus,
    selectFile,
    selectedFile,
    startAnalysis,
    status,
    statusText,
  } = useWorkbookAnalysis()
  const [isHistoryOpen, setIsHistoryOpen] = useState(false)

  return (
    <div className="space-y-7">
      <AnalysisFeedback feedback={feedback} />
      <div className="page-reveal">
        <AnalysisHeader status={status} statusText={statusText} />
      </div>

      <section className="page-reveal page-reveal-delay-1 grid gap-5 xl:grid-cols-[minmax(0,1fr)_20rem]">
        <AnalysisUploadPanel
          errorMessage={errorMessage}
          depth={depth}
          isPending={isPending}
          mode={mode}
          onClearFile={clearFile}
          onDepthChange={changeDepth}
          onModeChange={changeMode}
          onSelectFile={selectFile}
          onStartAnalysis={startAnalysis}
          onOpenHistory={() => setIsHistoryOpen(true)}
          selectedFile={selectedFile}
          status={status}
        />
        <aside>
          <AnalysisFlowPanel
            activeStep={activeStep}
            processingStatus={processingStatus}
            status={status}
          />
        </aside>
      </section>

      {analysisResult && analysisResultMode && (
        <AnalysisResultSection mode={analysisResultMode} result={analysisResult} />
      )}

      {isHistoryOpen && (
        <AnalysisHistoryDialog
          activeAnalysisId={activeAnalysisId}
          onClose={() => setIsHistoryOpen(false)}
          onOpen={(analysisId) => {
            openAnalysis(analysisId)
            setIsHistoryOpen(false)
          }}
        />
      )}
    </div>
  )
}

export default AnalysisPage
