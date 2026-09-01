import { BrainCircuit } from 'lucide-react'

import type { SheetResult } from '@/api/analysis'
import {
  AnalysisDecisionBadge,
  ImportanceBadge,
  SheetRoleBadge,
} from '@/components/analysis/workbook/semantic/components/ClassificationBadges'
import ClassificationReasonPanel from '@/components/analysis/workbook/semantic/components/ClassificationReasonPanel'
import { getSheetSemanticMetadata } from '@/components/analysis/workbook/semantic/semanticModel'
import { SHEET_ROLE_PRESENTATION } from '@/components/analysis/workbook/semantic/sheetRolePresentation'

const SheetSemanticSummary = ({ sheet }: { sheet: SheetResult }) => {
  const { analysisInclusion, classification } = getSheetSemanticMetadata(sheet)
  if (!classification) return null

  const presentation = SHEET_ROLE_PRESENTATION[classification.role]

  return (
    <section className="border-t border-slate-100 px-5 py-4">
      <div
        className={`rounded-2xl border-l-4 p-4 ${presentation.surfaceClass} ${presentation.borderClass}`}
      >
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div className="flex items-start gap-3">
            <span className="grid size-9 shrink-0 place-items-center rounded-xl bg-white text-brand-600 shadow-sm">
              <BrainCircuit aria-hidden="true" size={16} />
            </span>
            <div>
              <p className="text-[10px] font-extrabold tracking-[0.14em] text-slate-400">
                시트 의미 분석
              </p>
              <p className="mt-1 text-sm font-extrabold text-slate-800">
                {presentation.description}
              </p>
            </div>
          </div>
          <div className="flex flex-wrap gap-2">
            <SheetRoleBadge role={classification.role} />
            <ImportanceBadge importance={classification.importance} />
            {analysisInclusion && (
              <AnalysisDecisionBadge decision={analysisInclusion.decision} />
            )}
          </div>
        </div>

        <details className="mt-3">
          <summary className="cursor-pointer list-none text-[11px] font-bold text-brand-700 marker:hidden">
            분류 근거와 신뢰도 보기
          </summary>
          <div className="mt-3">
            <ClassificationReasonPanel
              analysisInclusion={analysisInclusion}
              confidence={classification.confidence}
              reasons={classification.reasons}
              title={`시트 역할 판단 · 구조상 중심도 점수 ${classification.importanceScore}`}
            />
          </div>
        </details>
      </div>
    </section>
  )
}

export default SheetSemanticSummary
