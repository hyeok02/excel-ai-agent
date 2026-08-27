import type {
  SemanticSheetImportance,
  SemanticSheetRole,
} from '@/components/analysis/workbook/semantic/semanticModel'
import type { RolePresentation } from '@/components/analysis/workbook/semantic/semanticRolePresentation'

export const SHEET_ROLE_PRESENTATION = {
  input: {
    label: '입력 시트',
    description: '사용자가 값을 입력하거나 수정하는 시트',
    badgeClass: 'bg-sky-50 text-sky-700 ring-sky-200',
    surfaceClass: 'bg-sky-50/60',
    borderClass: 'border-l-sky-400',
  },
  calculation: {
    label: '계산 시트',
    description: '수식과 참조를 이용해 중간 결과를 만드는 시트',
    badgeClass: 'bg-orange-50 text-orange-700 ring-orange-200',
    surfaceClass: 'bg-orange-50/60',
    borderClass: 'border-l-orange-400',
  },
  output: {
    label: '출력 시트',
    description: '보고와 의사결정에 사용하는 결과 시트',
    badgeClass: 'bg-emerald-50 text-emerald-700 ring-emerald-200',
    surfaceClass: 'bg-emerald-50/60',
    borderClass: 'border-l-emerald-400',
  },
  documentation: {
    label: '설명 시트',
    description: '사용 방법과 워크북 맥락을 제공하는 시트',
    badgeClass: 'bg-violet-50 text-violet-700 ring-violet-200',
    surfaceClass: 'bg-violet-50/60',
    borderClass: 'border-l-violet-400',
  },
  system: {
    label: '시스템 시트',
    description: '애드인·캐시 등 시스템이 사용하는 시트',
    badgeClass: 'bg-slate-100 text-slate-600 ring-slate-200',
    surfaceClass: 'bg-slate-50',
    borderClass: 'border-l-slate-400',
  },
} as const satisfies Record<SemanticSheetRole, RolePresentation>

export const SHEET_IMPORTANCE_PRESENTATION = {
  low: { label: '구조상 중심도 · 낮음', className: 'bg-slate-100 text-slate-600' },
  medium: { label: '구조상 중심도 · 보통', className: 'bg-blue-50 text-blue-700' },
  high: { label: '구조상 중심도 · 높음', className: 'bg-amber-50 text-amber-700' },
  critical: { label: '구조상 중심도 · 핵심', className: 'bg-red-50 text-red-700' },
} as const satisfies Record<SemanticSheetImportance, { label: string; className: string }>
