import { AlertTriangle, Braces, GitBranch, Network, Waypoints } from 'lucide-react'

import type { DependencyGraphResult } from '@/api/analysis'

interface DependencySummaryGridProps {
  graph: DependencyGraphResult
}

const DependencySummaryGrid = ({ graph }: DependencySummaryGridProps) => {
  const cycleCount = graph.cycleCount ?? 0
  const summaryItems = [
    { label: '관련 셀', value: graph.nodeCount, icon: Network, warning: false },
    { label: '수식 셀', value: graph.formulaNodeCount, icon: Braces, warning: false },
    { label: '참조 관계', value: graph.edgeCount, icon: GitBranch, warning: false },
    {
      label: '시트 간 참조',
      value: graph.crossSheetEdgeCount,
      icon: Waypoints,
      warning: false,
    },
    {
      label: '순환 참조',
      value: cycleCount,
      icon: AlertTriangle,
      warning: cycleCount > 0,
    },
  ] as const

  return (
    <div className="grid gap-3 p-5 sm:grid-cols-2 xl:grid-cols-5 md:p-6">
      {summaryItems.map(({ label, value, icon: Icon, warning }) => (
        <div
          className={`rounded-2xl p-4 ${warning ? 'bg-red-50' : 'bg-slate-50'}`}
          key={label}
        >
          <div className="flex items-center justify-between gap-3">
            <p
              className={`text-xs font-semibold ${warning ? 'text-red-500' : 'text-slate-400'}`}
            >
              {label}
            </p>
            <Icon
              aria-hidden="true"
              className={warning ? 'text-red-500' : 'text-brand-500'}
              size={16}
            />
          </div>
          <p
            className={`mt-2 text-2xl font-extrabold tracking-tight ${warning ? 'text-red-700' : 'text-slate-900'}`}
          >
            {value.toLocaleString()}
          </p>
        </div>
      ))}
    </div>
  )
}

export default DependencySummaryGrid
