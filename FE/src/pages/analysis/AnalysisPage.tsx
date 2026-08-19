import AnalysisFeedback from '@/components/analysis/AnalysisFeedback'
import AnalysisFlowPanel from '@/components/analysis/AnalysisFlowPanel'
import AnalysisHeader from '@/components/analysis/AnalysisHeader'
import AnalysisResultSection from '@/components/analysis/AnalysisResultSection'
import AnalysisUploadPanel from '@/components/analysis/AnalysisUploadPanel'
import { useWorkbookAnalysis } from '@/hooks/useWorkbookAnalysis'

const AnalysisPage = () => {
  const {
    analysisResult,
    clearFile,
    errorMessage,
    feedback,
    isPending,
    mode,
    selectFile,
    selectedFile,
    setMode,
    startAnalysis,
    status,
    statusText,
  } = useWorkbookAnalysis()

  return (
    <div className="space-y-7">
      <AnalysisFeedback feedback={feedback} />
      <AnalysisHeader status={status} statusText={statusText} />

      <section className="grid gap-5 xl:grid-cols-[minmax(0,1fr)_20rem]">
        <AnalysisUploadPanel
          errorMessage={errorMessage}
          isPending={isPending}
          mode={mode}
          onClearFile={clearFile}
          onModeChange={setMode}
          onSelectFile={selectFile}
          onStartAnalysis={startAnalysis}
          selectedFile={selectedFile}
        />
        <aside>
          <AnalysisFlowPanel />
        </aside>
      </section>

      {analysisResult && <AnalysisResultSection result={analysisResult} />}
    </div>
  )
}

export default AnalysisPage
