import type { DependencyClusterResult } from '@/api/analysis'
import { groupRelationships } from '@/components/analysis/result/dependency/dependencyMapUtils'
import DependencyRelationshipRow from '@/components/analysis/result/dependency/DependencyRelationshipRow'

interface DependencyClusterCardProps {
  cluster: DependencyClusterResult
}

const DependencyClusterCard = ({ cluster }: DependencyClusterCardProps) => {
  const relationships = groupRelationships(cluster)
  const visibleRelationships = relationships.slice(0, 4)
  const sheetDescription =
    cluster.sheetNames.length === 1
      ? `${cluster.sheetNames[0]} 시트의 주요 계산 흐름`
      : `${cluster.sheetNames.length}개 시트가 연결된 계산 흐름`

  return (
    <article className="rounded-3xl border border-slate-200 bg-slate-50/60 p-5 md:p-6">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h4 className="text-sm font-extrabold text-slate-950">{sheetDescription}</h4>
          <p className="mt-1 text-xs leading-5 text-slate-500">
            {cluster.formulaCount.toLocaleString()}개 수식이{' '}
            {cluster.nodeCount.toLocaleString()}개 관련 셀과 연결되어 있어요.
          </p>
        </div>
        <span className="rounded-xl bg-white px-3 py-2 text-[11px] font-bold text-slate-500 shadow-sm">
          주요 영향 관계 {relationships.length.toLocaleString()}개
        </span>
      </div>

      <div className="mt-4 grid gap-3 xl:grid-cols-2">
        {visibleRelationships.map((relationship) => (
          <DependencyRelationshipRow
            key={`${relationship.targetLabel}-${relationship.sourceLabels.join('|')}`}
            relationship={relationship}
          />
        ))}
      </div>

      {(cluster.truncated || relationships.length > visibleRelationships.length) && (
        <p className="mt-4 text-[11px] leading-5 text-slate-400">
          복잡한 계산 묶음은 영향이 큰 대표 관계만 보여줘요. 전체 개수에는 모든 셀과
          수식이 반영됩니다.
        </p>
      )}
    </article>
  )
}

export default DependencyClusterCard
