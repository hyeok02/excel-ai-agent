import { ChevronDown, Network } from 'lucide-react'
import { useState } from 'react'

import type { DependencyGraphResult } from '@/api/analysis'
import DependencyCycleSection from '@/components/analysis/result/dependency/DependencyCycleSection'
import DependencySummaryGrid from '@/components/analysis/result/dependency/DependencySummaryGrid'
import RelationshipPatternGrid from '@/components/analysis/result/dependency/RelationshipPatternGrid'
import { groupClusterPatterns } from '@/components/analysis/result/dependency/relationshipPatterns'

interface DependencyMapSectionProps {
  graph: DependencyGraphResult
}

const DEFAULT_VISIBLE_PATTERN_COUNT = 6

const DependencyMapSection = ({ graph }: DependencyMapSectionProps) => {
  const [isOpen, setIsOpen] = useState(true)
  const patterns = groupClusterPatterns(graph.clusters)
  const visiblePatterns = patterns.slice(0, DEFAULT_VISIBLE_PATTERN_COUNT)
  const hiddenPatterns = patterns.slice(DEFAULT_VISIBLE_PATTERN_COUNT)
  const cycleSummary =
    graph.cycleCount > 0
      ? `순환 참조 ${graph.cycleCount.toLocaleString()}개는 확인이 필요합니다.`
      : '순환 참조는 없습니다.'

  return (
    <details
      className="group mt-6 overflow-hidden rounded-3xl border border-brand-100 bg-white"
      onToggle={(event) => setIsOpen(event.currentTarget.open)}
      open={isOpen}
    >
      <summary className="flex cursor-pointer list-none flex-wrap items-center justify-between gap-4 bg-gradient-to-r from-brand-50/80 to-white p-5 marker:hidden md:p-6">
        <div>
          <div className="flex items-center gap-2 text-brand-700">
            <Network aria-hidden="true" size={18} />
            <span className="text-xs font-extrabold tracking-[0.12em]">
              BFS 계산 구조
            </span>
          </div>
          <h3 className="mt-2 text-lg font-extrabold text-slate-950">
            수식 연결과 계산 방식
          </h3>
          <p className="mt-1 text-sm leading-6 text-slate-500">
            서로 독립된 계산 흐름이 {graph.clusterCount.toLocaleString()}개입니다. 대표
            계산 방식은 한눈에 보고, 셀 위치와 원본 수식은 필요할 때 확인할 수 있습니다.{' '}
            {cycleSummary}
          </p>
        </div>
        <span className="inline-flex items-center gap-2 rounded-xl border border-brand-100 bg-white px-3 py-2 text-xs font-bold text-brand-700 shadow-sm">
          {isOpen ? '접기' : '자세히 보기'}
          <ChevronDown
            aria-hidden="true"
            className="transition-transform group-open:rotate-180"
            size={15}
          />
        </span>
      </summary>

      <div className="border-t border-brand-100">
        <DependencySummaryGrid graph={graph} />

        <DependencyCycleSection
          cycleCount={graph.cycleCount ?? 0}
          cycles={graph.cycles ?? []}
          cyclicNodeCount={graph.cyclicNodeCount ?? 0}
        />

        {visiblePatterns.length > 0 && (
          <div className="px-5 pb-5 md:px-6 md:pb-6">
            <RelationshipPatternGrid patterns={visiblePatterns} />
            {hiddenPatterns.length > 0 && (
              <details className="mt-4 rounded-2xl border border-brand-100 bg-brand-50/40 p-3">
                <summary className="cursor-pointer list-none text-center text-xs font-bold text-brand-700 marker:hidden">
                  다른 계산 방식 {hiddenPatterns.length}개 보기
                </summary>
                <div className="mt-3">
                  <RelationshipPatternGrid patterns={hiddenPatterns} />
                </div>
              </details>
            )}
          </div>
        )}
      </div>
    </details>
  )
}

export default DependencyMapSection
