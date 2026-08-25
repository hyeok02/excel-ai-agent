import clsx from 'clsx'
import { CheckCircle2, CircleOff } from 'lucide-react'

import type { AnalysisDecision, SemanticRole } from '@/api/analysis'
import type {
  SemanticSheetImportance,
  SemanticSheetRole,
} from '@/components/analysis/workbook/semantic/semanticModel'
import { SEMANTIC_ROLE_PRESENTATION } from '@/components/analysis/workbook/semantic/semanticRolePresentation'
import {
  SHEET_IMPORTANCE_PRESENTATION,
  SHEET_ROLE_PRESENTATION,
} from '@/components/analysis/workbook/semantic/sheetRolePresentation'

interface SemanticRoleBadgeProps {
  role: SemanticRole
  compact?: boolean
}

export const SemanticRoleBadge = ({ role, compact = false }: SemanticRoleBadgeProps) => {
  const presentation = SEMANTIC_ROLE_PRESENTATION[role]
  return (
    <span
      className={clsx(
        'inline-flex shrink-0 items-center rounded-lg font-extrabold ring-1 ring-inset',
        compact ? 'px-1.5 py-0.5 text-[9px]' : 'px-2.5 py-1.5 text-[11px]',
        presentation.badgeClass,
      )}
      title={presentation.description}
    >
      {presentation.label}
    </span>
  )
}

export const SheetRoleBadge = ({ role }: { role: SemanticSheetRole }) => {
  const presentation = SHEET_ROLE_PRESENTATION[role]
  return (
    <span
      className={clsx(
        'inline-flex items-center rounded-lg px-2.5 py-1.5 text-[11px] font-extrabold ring-1 ring-inset',
        presentation.badgeClass,
      )}
      title={presentation.description}
    >
      {presentation.label}
    </span>
  )
}

export const ImportanceBadge = ({
  importance,
}: {
  importance: SemanticSheetImportance
}) => {
  const presentation = SHEET_IMPORTANCE_PRESENTATION[importance]
  return (
    <span
      className={clsx(
        'inline-flex items-center rounded-lg px-2.5 py-1.5 text-[11px] font-bold',
        presentation.className,
      )}
    >
      {presentation.label}
    </span>
  )
}

export const AnalysisDecisionBadge = ({ decision }: { decision: AnalysisDecision }) => {
  const included = decision === 'include'
  const Icon = included ? CheckCircle2 : CircleOff
  return (
    <span
      className={clsx(
        'inline-flex items-center gap-1.5 rounded-lg px-2.5 py-1.5 text-[11px] font-extrabold',
        included ? 'bg-emerald-50 text-emerald-700' : 'bg-slate-100 text-slate-600',
      )}
    >
      <Icon aria-hidden="true" size={12} />
      {included ? '분석 포함' : '분석 제외'}
    </span>
  )
}
