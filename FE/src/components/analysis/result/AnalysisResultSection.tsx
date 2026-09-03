import type { AnalysisMode, AnalysisResultDetails } from '@/api/analysis'
import AdvancedAnalysisSection from '@/components/analysis/result/AdvancedAnalysisSection'
import AgentReadySection from '@/components/analysis/result/AgentReadySection'
import AnalysisResultHeader from '@/components/analysis/result/AnalysisResultHeader'
import AnalysisResultSummary from '@/components/analysis/result/AnalysisResultSummary'
import BfsAnalysisWorkspace from '@/components/analysis/result/bfs/BfsAnalysisWorkspace'
import FormulaRiskSection from '@/components/analysis/result/formula-risk/FormulaRiskSection'
import InsightReportSection from '@/components/analysis/result/InsightReportSection'
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

      {mode === 'BFS' && (
        <BfsAnalysisWorkspace key={`${result.analysisId}-${mode}`} workbook={workbook} />
      )}

      {mode === 'LLM' && (
        <>
          <WorkbookQuestionSection analysisId={result.analysisId} />
          <WorkbookWritebackSection analysisId={result.analysisId} />
          <AdvancedAnalysisSection>
            <WorkbookSemanticOverview
              excludedSheets={workbook.excludedSheets ?? []}
              sheets={workbook.sheets}
            />

            {workbook.formulaRiskSummary && (
              <FormulaRiskSection summary={workbook.formulaRiskSummary} />
            )}

            <WorkbookExplorer sheets={workbook.sheets} />
          </AdvancedAnalysisSection>

          <AgentReadySection hasInsightReport={result.insightReport !== null} />
        </>
      )}
    </section>
  )
}

export default AnalysisResultSection
