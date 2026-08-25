import type { SemanticRole } from '@/api/analysis'

export interface RolePresentation {
  label: string
  description: string
  badgeClass: string
  surfaceClass: string
  borderClass: string
}

export const SEMANTIC_ROLE_PRESENTATION: Record<SemanticRole, RolePresentation> = {
  title: {
    label: '제목',
    description: '표나 보고서의 주제를 설명하는 영역',
    badgeClass: 'bg-violet-50 text-violet-700 ring-violet-200',
    surfaceClass: 'bg-violet-50/60',
    borderClass: 'border-l-violet-400',
  },
  description: {
    label: '설명',
    description: '데이터의 목적과 맥락을 설명하는 문장 영역',
    badgeClass: 'bg-slate-100 text-slate-700 ring-slate-200',
    surfaceClass: 'bg-slate-50',
    borderClass: 'border-l-slate-400',
  },
  unit: {
    label: '단위',
    description: '금액·비율·인원 등 값의 해석 기준',
    badgeClass: 'bg-cyan-50 text-cyan-700 ring-cyan-200',
    surfaceClass: 'bg-cyan-50/60',
    borderClass: 'border-l-cyan-400',
  },
  header: {
    label: '헤더',
    description: '열과 행 데이터의 의미를 정의하는 영역',
    badgeClass: 'bg-indigo-50 text-indigo-700 ring-indigo-200',
    surfaceClass: 'bg-indigo-50/60',
    borderClass: 'border-l-indigo-400',
  },
  data: {
    label: '데이터',
    description: '분석의 기반이 되는 반복 데이터 영역',
    badgeClass: 'bg-blue-50 text-blue-700 ring-blue-200',
    surfaceClass: 'bg-blue-50/50',
    borderClass: 'border-l-blue-400',
  },
  formula: {
    label: '수식',
    description: 'Excel 수식으로 계산되는 셀',
    badgeClass: 'bg-amber-50 text-amber-700 ring-amber-200',
    surfaceClass: 'bg-amber-50/60',
    borderClass: 'border-l-amber-400',
  },
  note: {
    label: '주석',
    description: '참고 또는 보충 설명을 제공하는 영역',
    badgeClass: 'bg-yellow-50 text-yellow-700 ring-yellow-200',
    surfaceClass: 'bg-yellow-50/60',
    borderClass: 'border-l-yellow-400',
  },
  total: {
    label: '합계·소계',
    description: '데이터를 집계한 결과 영역',
    badgeClass: 'bg-emerald-50 text-emerald-700 ring-emerald-200',
    surfaceClass: 'bg-emerald-50/60',
    borderClass: 'border-l-emerald-400',
  },
  input: {
    label: '입력',
    description: '사용자가 입력하거나 변경하는 값 영역',
    badgeClass: 'bg-sky-50 text-sky-700 ring-sky-200',
    surfaceClass: 'bg-sky-50/60',
    borderClass: 'border-l-sky-400',
  },
  calculation: {
    label: '계산',
    description: '입력값을 바탕으로 중간 결과를 계산하는 영역',
    badgeClass: 'bg-orange-50 text-orange-700 ring-orange-200',
    surfaceClass: 'bg-orange-50/60',
    borderClass: 'border-l-orange-400',
  },
  output: {
    label: '출력',
    description: '판단에 직접 사용하는 최종 결과 영역',
    badgeClass: 'bg-green-50 text-green-700 ring-green-200',
    surfaceClass: 'bg-green-50/60',
    borderClass: 'border-l-green-400',
  },
  instruction: {
    label: '안내',
    description: '워크북 사용 방법을 설명하는 영역',
    badgeClass: 'bg-purple-50 text-purple-700 ring-purple-200',
    surfaceClass: 'bg-purple-50/60',
    borderClass: 'border-l-purple-400',
  },
  warning: {
    label: '주의',
    description: '사용자가 확인해야 할 주의·경고 영역',
    badgeClass: 'bg-red-50 text-red-700 ring-red-200',
    surfaceClass: 'bg-red-50/60',
    borderClass: 'border-l-red-400',
  },
  source_note: {
    label: '출처',
    description: '데이터 출처와 기준일을 설명하는 영역',
    badgeClass: 'bg-teal-50 text-teal-700 ring-teal-200',
    surfaceClass: 'bg-teal-50/60',
    borderClass: 'border-l-teal-400',
  },
  rule_note: {
    label: '판단 기준',
    description: '결과를 해석하는 조건과 기준을 설명하는 영역',
    badgeClass: 'bg-fuchsia-50 text-fuchsia-700 ring-fuchsia-200',
    surfaceClass: 'bg-fuchsia-50/60',
    borderClass: 'border-l-fuchsia-400',
  },
  system_cache: {
    label: '시스템',
    description: '업무 분석에서 제외되는 시스템 데이터 영역',
    badgeClass: 'bg-slate-100 text-slate-600 ring-slate-200',
    surfaceClass: 'bg-slate-50',
    borderClass: 'border-l-slate-400',
  },
  ignore: {
    label: '제외',
    description: '분석에 사용하지 않는 영역',
    badgeClass: 'bg-stone-100 text-stone-600 ring-stone-200',
    surfaceClass: 'bg-stone-50',
    borderClass: 'border-l-stone-400',
  },
  unknown: {
    label: '미분류',
    description: '현재 규칙으로 역할을 확정하지 못한 영역',
    badgeClass: 'bg-slate-100 text-slate-600 ring-slate-200',
    surfaceClass: 'bg-slate-50',
    borderClass: 'border-l-slate-300',
  },
}
