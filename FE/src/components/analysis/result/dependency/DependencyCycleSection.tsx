import { AlertTriangle, ArrowRight, ChevronDown } from 'lucide-react'

import type { DependencyCycleResult } from '@/api/analysis'

interface DependencyCycleSectionProps {
  cycleCount: number
  cyclicNodeCount: number
  cycles: DependencyCycleResult[]
}

const DependencyCycleSection = ({
  cycleCount,
  cyclicNodeCount,
  cycles,
}: DependencyCycleSectionProps) => {
  if (cycleCount === 0) return null

  return (
    <section className="mx-5 mb-5 overflow-hidden rounded-2xl border border-red-200 bg-red-50/60 md:mx-6 md:mb-6">
      <div className="flex items-start gap-3 border-b border-red-100 p-4">
        <span className="grid size-9 shrink-0 place-items-center rounded-xl bg-red-100 text-red-600">
          <AlertTriangle aria-hidden="true" size={18} />
        </span>
        <div>
          <h4 className="text-sm font-extrabold text-red-900">
            순환 참조 {cycleCount.toLocaleString()}개가 감지되었습니다
          </h4>
          <p className="mt-1 text-xs leading-5 text-red-700/80">
            {cyclicNodeCount.toLocaleString()}개 수식 셀이 서로를 다시 참조합니다. 계산
            결과가 불안정하거나 Excel에서 순환 참조 경고가 발생할 수 있습니다.
          </p>
        </div>
      </div>

      <div className="space-y-2 p-3">
        {cycles.slice(0, 4).map((cycle, cycleIndex) => {
          const nodeLabels = new Map(cycle.nodes.map((node) => [node.id, node.label]))

          return (
            <details className="rounded-xl border border-red-100 bg-white" key={cycle.id}>
              <summary className="flex cursor-pointer list-none items-center justify-between gap-3 px-4 py-3 marker:hidden">
                <div>
                  <p className="text-xs font-extrabold text-slate-800">
                    순환 그룹 {cycleIndex + 1}
                  </p>
                  <p className="mt-1 text-[11px] text-slate-400">
                    {cycle.sheetNames.join(', ') || '시트 확인 불가'} · 셀{' '}
                    {cycle.nodeCount}개 · 관계 {cycle.edgeCount}개
                  </p>
                </div>
                <ChevronDown
                  aria-hidden="true"
                  className="shrink-0 text-red-400"
                  size={16}
                />
              </summary>

              <div className="space-y-2 border-t border-red-100 p-3">
                {cycle.edges.map((edge, edgeIndex) => (
                  <div
                    className="flex flex-wrap items-center gap-2 rounded-lg bg-slate-50 px-3 py-2 text-xs text-slate-600"
                    key={`${edge.source}-${edge.target}-${edgeIndex}`}
                  >
                    <span className="font-bold text-slate-700">
                      {nodeLabels.get(edge.source) ?? edge.source}
                    </span>
                    <ArrowRight aria-hidden="true" className="text-red-400" size={14} />
                    <span className="font-bold text-slate-700">
                      {nodeLabels.get(edge.target) ?? edge.target}
                    </span>
                  </div>
                ))}
                {cycle.truncated && (
                  <p className="text-[11px] text-slate-400">
                    순환 그룹이 커서 일부 셀과 참조 관계만 표시합니다.
                  </p>
                )}
              </div>
            </details>
          )
        })}
        {cycleCount > cycles.length && (
          <p className="px-1 text-[11px] text-red-600/70">
            순환 그룹이 많아 영향도가 큰 {cycles.length}개 그룹만 제공합니다.
          </p>
        )}
      </div>
    </section>
  )
}

export default DependencyCycleSection
