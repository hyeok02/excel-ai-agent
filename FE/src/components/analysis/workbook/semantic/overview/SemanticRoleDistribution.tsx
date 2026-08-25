import type { SemanticRole } from '@/api/analysis'
import {
  SemanticRoleBadge,
  SheetRoleBadge,
} from '@/components/analysis/workbook/semantic/components/ClassificationBadges'
import type { SemanticSheetRole } from '@/components/analysis/workbook/semantic/semanticModel'

interface SemanticRoleDistributionProps {
  regionRoleCounts: [SemanticRole, number][]
  sheetRoleCounts: [SemanticSheetRole, number][]
}

const RoleCount = ({ badge, count }: { badge: React.ReactNode; count: number }) => (
  <span className="inline-flex items-center gap-1">
    {badge}
    <b className="text-xs text-slate-500">{count}</b>
  </span>
)

const SemanticRoleDistribution = ({
  regionRoleCounts,
  sheetRoleCounts,
}: SemanticRoleDistributionProps) => (
  <div className="grid gap-5 p-5 lg:grid-cols-2 md:p-6">
    <div>
      <p className="text-xs font-extrabold text-slate-700">시트 역할 구성</p>
      <div className="mt-3 flex flex-wrap gap-2">
        {sheetRoleCounts.length > 0 ? (
          sheetRoleCounts.map(([role, count]) => (
            <RoleCount badge={<SheetRoleBadge role={role} />} count={count} key={role} />
          ))
        ) : (
          <span className="text-xs text-slate-400">분류된 시트가 없습니다.</span>
        )}
      </div>
    </div>
    <div>
      <p className="text-xs font-extrabold text-slate-700">영역 역할 구성</p>
      <div className="mt-3 flex flex-wrap gap-2">
        {regionRoleCounts.length > 0 ? (
          regionRoleCounts.map(([role, count]) => (
            <RoleCount
              badge={<SemanticRoleBadge role={role} />}
              count={count}
              key={role}
            />
          ))
        ) : (
          <span className="text-xs text-slate-400">분류된 영역이 없습니다.</span>
        )}
      </div>
    </div>
  </div>
)

export default SemanticRoleDistribution
