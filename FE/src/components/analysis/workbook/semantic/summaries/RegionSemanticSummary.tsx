import type { RegionResult } from '@/api/analysis'
import {
  AnalysisDecisionBadge,
  SemanticRoleBadge,
} from '@/components/analysis/workbook/semantic/components/ClassificationBadges'
import ClassificationReasonPanel from '@/components/analysis/workbook/semantic/components/ClassificationReasonPanel'
import { SEMANTIC_ROLE_PRESENTATION } from '@/components/analysis/workbook/semantic/semanticRolePresentation'

interface RegionSemanticSummaryProps {
  region: RegionResult
}

export const RegionSemanticBadges = ({ region }: RegionSemanticSummaryProps) => {
  return (
    <div className="flex flex-wrap items-center gap-1.5">
      {region.semantic && <SemanticRoleBadge role={region.semantic.role} />}
      {region.analysisInclusion && (
        <AnalysisDecisionBadge decision={region.analysisInclusion.decision} />
      )}
    </div>
  )
}

const RegionSemanticSummary = ({ region }: RegionSemanticSummaryProps) => {
  const semantic = region.semantic
  if (!semantic) {
    return (
      <div className="mb-3 rounded-xl border border-dashed border-slate-200 bg-slate-50 p-3 text-xs text-slate-400">
        이 영역에는 아직 의미 분류 결과가 없습니다.
      </div>
    )
  }

  const presentation = SEMANTIC_ROLE_PRESENTATION[semantic.role]

  return (
    <div
      className={`mb-3 rounded-xl border-l-4 p-3.5 ${presentation.surfaceClass} ${presentation.borderClass}`}
    >
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <p className="text-[10px] font-extrabold tracking-[0.14em] text-slate-400">
            영역 의미 분석
          </p>
          <p className="mt-1 text-xs font-semibold leading-5 text-slate-700">
            {presentation.description}
          </p>
        </div>
        <RegionSemanticBadges region={region} />
      </div>
      <div className="mt-3">
        <ClassificationReasonPanel
          analysisInclusion={region.analysisInclusion}
          confidence={semantic.confidence}
          reasons={semantic.reasons}
          title="영역 역할 판단 근거"
        />
      </div>
    </div>
  )
}

export default RegionSemanticSummary
