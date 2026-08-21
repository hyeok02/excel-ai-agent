import { Network } from 'lucide-react'

import type { AnalysisMode, DependencyGraphResult } from '@/api/analysis'
import DependencyClusterCard from '@/components/analysis/result/dependency/DependencyClusterCard'
import DependencyCycleSection from '@/components/analysis/result/dependency/DependencyCycleSection'
import DependencySummaryGrid from '@/components/analysis/result/dependency/DependencySummaryGrid'

interface DependencyMapSectionProps {
  graph: DependencyGraphResult
  mode: AnalysisMode
}

const COPY_BY_MODE = {
  BFS: {
    eyebrow: 'BFS CLUSTER MAP',
    title: '수식 연결 군집',
    description: '서로 참조하는 셀을 BFS로 탐색해 독립적인 계산 흐름 단위로 묶었어요.',
  },
  LLM: {
    eyebrow: 'FORMULA IMPACT',
    title: 'AI 판단의 구조적 근거',
    description:
      'AI가 판단에 사용한 입력 셀과 계산 결과 사이의 영향 관계를 확인할 수 있어요.',
  },
} as const

const DependencyMapSection = ({ graph, mode }: DependencyMapSectionProps) => {
  const copy = COPY_BY_MODE[mode]

  return (
    <section className="mt-6 overflow-hidden rounded-3xl border border-brand-100 bg-white">
      <div className="flex flex-wrap items-start justify-between gap-4 border-b border-brand-100 bg-gradient-to-r from-brand-50/80 to-white p-5 md:p-6">
        <div>
          <div className="flex items-center gap-2 text-brand-700">
            <Network aria-hidden="true" size={18} />
            <span className="text-xs font-extrabold tracking-[0.16em]">
              {copy.eyebrow}
            </span>
          </div>
          <h3 className="mt-2 text-lg font-extrabold text-slate-950">{copy.title}</h3>
          <p className="mt-1 text-sm leading-6 text-slate-500">{copy.description}</p>
        </div>
        <span className="rounded-xl border border-brand-100 bg-white px-3 py-2 text-xs font-bold text-brand-700 shadow-sm">
          계산 흐름 {graph.clusterCount.toLocaleString()}개
        </span>
      </div>

      <DependencySummaryGrid graph={graph} />

      <DependencyCycleSection
        cycleCount={graph.cycleCount ?? 0}
        cycles={graph.cycles ?? []}
        cyclicNodeCount={graph.cyclicNodeCount ?? 0}
      />

      {graph.clusters.length > 0 && (
        <div className="space-y-4 px-5 pb-5 md:px-6 md:pb-6">
          {graph.clusters.slice(0, 4).map((cluster) => (
            <DependencyClusterCard cluster={cluster} key={cluster.id} />
          ))}
          {graph.clusters.length > 4 && (
            <p className="text-center text-[11px] text-slate-400">
              영향도가 큰 계산 흐름 4개를 우선 표시했습니다.
            </p>
          )}
        </div>
      )}
    </section>
  )
}

export default DependencyMapSection
