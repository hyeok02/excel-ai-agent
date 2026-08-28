import { AlertTriangle, Layers3, Waypoints } from 'lucide-react'

import type { DependencyGraphResult } from '@/api/analysis'

interface DependencySummaryGridProps {
  graph: DependencyGraphResult
}

const DependencySummaryGrid = ({ graph }: DependencySummaryGridProps) => {
  const cycleCount = graph.cycleCount ?? 0
  const summaryItems = [
    {
      label: '계산 묶음',
      summary: `${graph.clusterCount.toLocaleString()}개로 나뉩니다`,
      description: '서로 영향을 주지 않는 계산 흐름입니다.',
      icon: Layers3,
      warning: false,
    },
    {
      label: '다른 시트로 이어지는 영향',
      summary: `${graph.crossSheetEdgeCount.toLocaleString()}개 연결`,
      description: '값을 바꾸면 다른 시트의 결과도 달라질 수 있습니다.',
      icon: Waypoints,
      warning: false,
    },
    {
      label: '계산 오류 가능성',
      summary:
        cycleCount > 0
          ? `순환 참조 ${cycleCount.toLocaleString()}개 발견`
          : '순환 참조 없음',
      description:
        cycleCount > 0
          ? '서로를 다시 참조하는 수식은 확인이 필요합니다.'
          : '계산이 되돌아오는 구조는 발견되지 않았습니다.',
      icon: AlertTriangle,
      warning: cycleCount > 0,
    },
  ] as const

  return (
    <div className="grid gap-3 p-5 md:grid-cols-3 md:p-6">
      {summaryItems.map(({ label, summary, description, icon: Icon, warning }) => (
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
            className={`mt-2 text-base font-extrabold ${warning ? 'text-red-700' : 'text-slate-900'}`}
          >
            {summary}
          </p>
          <p
            className={`mt-1 text-xs leading-5 ${warning ? 'text-red-600/80' : 'text-slate-500'}`}
          >
            {description}
          </p>
        </div>
      ))}
    </div>
  )
}

export default DependencySummaryGrid
