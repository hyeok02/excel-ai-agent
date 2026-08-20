import { Network } from 'lucide-react'

import type { DependencyGraphResult } from '@/api/analysis'
import DependencyClusterCard from '@/components/analysis/result/dependency/DependencyClusterCard'
import DependencySummaryGrid from '@/components/analysis/result/dependency/DependencySummaryGrid'

interface DependencyMapSectionProps {
  graph: DependencyGraphResult
}

const DependencyMapSection = ({ graph }: DependencyMapSectionProps) => (
  <section className="mt-6 overflow-hidden rounded-3xl border border-brand-100 bg-white">
    <div className="flex flex-wrap items-start justify-between gap-4 border-b border-brand-100 bg-gradient-to-r from-brand-50/80 to-white p-5 md:p-6">
      <div>
        <div className="flex items-center gap-2 text-brand-700">
          <Network aria-hidden="true" size={18} />
          <span className="text-xs font-extrabold tracking-[0.16em]">FORMULA IMPACT</span>
        </div>
        <h3 className="mt-2 text-lg font-extrabold text-slate-950">수식 영향 관계</h3>
        <p className="mt-1 text-sm leading-6 text-slate-500">
          어떤 입력 셀과 범위가 계산 결과에 영향을 주는지 이해하기 쉽게 정리했어요.
        </p>
      </div>
      <span className="rounded-xl border border-brand-100 bg-white px-3 py-2 text-xs font-bold text-brand-700 shadow-sm">
        계산 흐름 {graph.clusterCount.toLocaleString()}개
      </span>
    </div>

    <DependencySummaryGrid graph={graph} />

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

export default DependencyMapSection
