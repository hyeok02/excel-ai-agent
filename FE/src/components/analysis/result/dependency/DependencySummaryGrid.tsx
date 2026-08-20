import { Braces, GitBranch, Network, Waypoints } from 'lucide-react'

import type { DependencyGraphResult } from '@/api/analysis'

interface DependencySummaryGridProps {
  graph: DependencyGraphResult
}

const DependencySummaryGrid = ({ graph }: DependencySummaryGridProps) => {
  const summaryItems = [
    { label: '관련 셀', value: graph.nodeCount, icon: Network },
    { label: '수식 셀', value: graph.formulaNodeCount, icon: Braces },
    { label: '참조 관계', value: graph.edgeCount, icon: GitBranch },
    { label: '시트 간 참조', value: graph.crossSheetEdgeCount, icon: Waypoints },
  ] as const

  return (
    <div className="grid gap-3 p-5 sm:grid-cols-2 xl:grid-cols-4 md:p-6">
      {summaryItems.map(({ label, value, icon: Icon }) => (
        <div className="rounded-2xl bg-slate-50 p-4" key={label}>
          <div className="flex items-center justify-between gap-3">
            <p className="text-xs font-semibold text-slate-400">{label}</p>
            <Icon aria-hidden="true" className="text-brand-500" size={16} />
          </div>
          <p className="mt-2 text-2xl font-extrabold tracking-tight text-slate-900">
            {value.toLocaleString()}
          </p>
        </div>
      ))}
    </div>
  )
}

export default DependencySummaryGrid
