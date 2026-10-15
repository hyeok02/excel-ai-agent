import type { AnalysisMode, AnalysisResultDetails } from '@/api/analysis'
import AdvancedAnalysisSection from '@/components/analysis/result/AdvancedAnalysisSection'
import AnalysisResultHeader from '@/components/analysis/result/AnalysisResultHeader'
import AnalysisResultSummary from '@/components/analysis/result/AnalysisResultSummary'
import BfsAnalysisWorkspace from '@/components/analysis/result/bfs/BfsAnalysisWorkspace'
import InsightReportSection from '@/components/analysis/result/InsightReportSection'
import { buildQuestionSuggestions } from '@/components/analysis/result/questions/questionPresentation'
import WorkbookQuestionSection from '@/components/analysis/result/questions/WorkbookQuestionSection'
import WorkbookWritebackSection from '@/components/analysis/result/writeback/WorkbookWritebackSection'
import WorkbookExplorer from '@/components/analysis/workbook/explorer/WorkbookExplorer'
import WorkbookSemanticOverview from '@/components/analysis/workbook/semantic/summaries/WorkbookSemanticOverview'

interface AnalysisResultSectionProps {
  executedMode: AnalysisMode
  mode: AnalysisMode
  result: AnalysisResultDetails
}

const AnalysisResultSection = ({
  executedMode,
  mode,
  result,
}: AnalysisResultSectionProps) => {
  const { workbook } = result

  return (
    <section className="panel p-5 md:p-7" aria-live="polite">
      <AnalysisResultHeader mode={executedMode} result={result} />
      <AnalysisResultSummary workbook={workbook} />

      {mode === 'LLM' && result.insightReport && (
        <InsightReportSection report={result.insightReport} />
      )}

      {mode === 'LLM' && (
        <WorkbookQuestionSection
          key={result.analysisId}
          analysisId={result.analysisId}
          insightReport={result.insightReport}
          sourceAvailable={result.sourceAvailable}
          suggestions={buildQuestionSuggestions(result.insightReport)}
        />
      )}

      {mode === 'BFS' && (
        <BfsAnalysisWorkspace key={`${result.analysisId}-${mode}`} workbook={workbook} />
      )}

      {mode === 'LLM' && (
        <>
          <WorkbookWritebackSection
            analysisId={result.analysisId}
            sourceAvailable={result.sourceAvailable}
          />
          <AdvancedAnalysisSection>
            <WorkbookSemanticOverview
              excludedSheets={workbook.excludedSheets ?? []}
              sheets={workbook.sheets}
            />

            <WorkbookExplorer sheets={workbook.sheets} />
          </AdvancedAnalysisSection>
        </>
      )}
    </section>
  )
}

export default AnalysisResultSection
