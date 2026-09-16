import clsx from 'clsx'
import { Check, CircleOff } from 'lucide-react'

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

/** 채운 배지 대신 점 하나로 역할을 표시한다. 목록에서 이름과 범위가 먼저 읽혀야 한다. */
export const SemanticRoleBadge = ({ role, compact = false }: SemanticRoleBadgeProps) => {
  const presentation = SEMANTIC_ROLE_PRESENTATION[role]
  return (
    <span
      className={clsx(
        'inline-flex shrink-0 items-center font-semibold text-slate-600',
        compact ? 'gap-1 text-[10px]' : 'gap-1.5 text-xs',
      )}
      title={presentation.description}
    >
      <span
        aria-hidden="true"
        className={clsx(
          'shrink-0 rounded-full',
          compact ? 'size-1.5' : 'size-[7px]',
          presentation.dotClass,
        )}
      />
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

/**
 * 분석 포함은 기본 상태라 조용히 둔다. 거의 모든 행에 붙는 배지는 정보가
 * 되지 못한다. 눈에 띄어야 하는 쪽은 제외된 영역이다.
 */
export const AnalysisDecisionBadge = ({ decision }: { decision: AnalysisDecision }) => {
  if (decision === 'include') {
    return (
      <span className="inline-flex items-center gap-1 text-xs font-medium text-slate-400">
        <Check aria-hidden="true" size={12} />
        포함
      </span>
    )
  }

  return (
    <span className="inline-flex items-center gap-1.5 rounded-md bg-slate-100 px-2 py-1 text-xs font-semibold text-slate-600">
      <CircleOff aria-hidden="true" size={12} />
      분석 제외
    </span>
  )
}
