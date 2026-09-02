import { Network } from 'lucide-react'
import { useState } from 'react'

import type { WorkbookResult } from '@/api/analysis'
import BfsAnalysisNavigation, {
  type BfsView,
} from '@/components/analysis/result/bfs/BfsAnalysisNavigation'
import DependencyMapSection from '@/components/analysis/result/DependencyMapSection'
import FormulaRiskSection from '@/components/analysis/result/formula-risk/FormulaRiskSection'
import WorkbookExplorer from '@/components/analysis/workbook/explorer/WorkbookExplorer'
import WorkbookSemanticOverview from '@/components/analysis/workbook/semantic/summaries/WorkbookSemanticOverview'

interface BfsAnalysisWorkspaceProps {
  workbook: WorkbookResult
}

const BfsAnalysisWorkspace = ({ workbook }: BfsAnalysisWorkspaceProps) => {
  const [activeView, setActiveView] = useState<BfsView>('flow')
  const graph = workbook.dependencyGraph
  const risks = workbook.formulaRiskSummary

  return (
    <section className="mt-6">
      <BfsAnalysisNavigation
        activeView={activeView}
        clusterCount={graph?.clusterCount ?? 0}
        onChange={setActiveView}
        riskCount={risks?.totalCount ?? 0}
        sheetCount={workbook.sheets.length}
      />

      <div id={`bfs-panel-${activeView}`} role="tabpanel">
        {activeView === 'flow' && graph && graph.nodeCount > 0 && (
          <DependencyMapSection compact graph={graph} />
        )}
        {activeView === 'flow' && (!graph || graph.nodeCount === 0) && (
          <div className="mt-4 rounded-3xl border border-slate-200 bg-white px-5 py-10 text-center">
            <Network aria-hidden="true" className="mx-auto text-slate-300" size={24} />
            <p className="mt-3 text-sm font-extrabold text-slate-800">
              연결된 수식 군집이 없습니다
            </p>
            <p className="mt-1 text-xs text-slate-500">
              셀 참조가 없거나 각 수식이 독립적으로 구성된 워크북입니다.
            </p>
          </div>
        )}
        {activeView === 'risk' && risks && <FormulaRiskSection summary={risks} />}
        {activeView === 'structure' && (
          <WorkbookSemanticOverview
            excludedSheets={workbook.excludedSheets ?? []}
            sheets={workbook.sheets}
          />
        )}
        {activeView === 'source' && <WorkbookExplorer sheets={workbook.sheets} />}
      </div>
    </section>
  )
}

export default BfsAnalysisWorkspace
