import type { SemanticRole } from '@/api/analysis'

export interface RolePresentation {
  label: string
  description: string
  dotClass: string
  surfaceClass: string
  borderClass: string
}

/**
 * 색은 다섯 갈래로만 쓴다.
 *
 * 역할마다 다른 색을 주면 열다섯 가지가 되어 외울 수가 없고, 색이 정보가
 * 아니라 장식이 된다. 의미가 같은 역할끼리 묶어야 색으로 구분이 된다.
 */
const FAMILY = {
  source: {
    dotClass: 'bg-blue-500',
    surfaceClass: 'bg-blue-50/50',
    borderClass: 'border-l-blue-400',
  },
  compute: {
    dotClass: 'bg-amber-500',
    surfaceClass: 'bg-amber-50/50',
    borderClass: 'border-l-amber-400',
  },
  result: {
    dotClass: 'bg-emerald-500',
    surfaceClass: 'bg-emerald-50/50',
    borderClass: 'border-l-emerald-400',
  },
  meta: {
    dotClass: 'bg-slate-400',
    surfaceClass: 'bg-slate-50',
    borderClass: 'border-l-slate-300',
  },
  caution: {
    dotClass: 'bg-rose-500',
    surfaceClass: 'bg-rose-50/50',
    borderClass: 'border-l-rose-400',
  },
} as const

const present = (
  family: keyof typeof FAMILY,
  label: string,
  description: string,
): RolePresentation => ({ ...FAMILY[family], label, description })

export const SEMANTIC_ROLE_PRESENTATION: Record<SemanticRole, RolePresentation> = {
  title: present('meta', '제목', '표나 보고서의 주제를 설명하는 영역'),
  description: present('meta', '설명', '데이터의 목적과 맥락을 설명하는 문장 영역'),
  unit: present('meta', '단위', '금액·비율·인원 등 값의 해석 기준'),
  header: present('source', '헤더', '열과 행 데이터의 의미를 정의하는 영역'),
  data: present('source', '데이터', '분석의 기반이 되는 반복 데이터 영역'),
  input: present('source', '입력', '사용자가 입력하거나 변경하는 값 영역'),
  formula: present('compute', '수식', 'Excel 수식으로 계산되는 셀'),
  calculation: present('compute', '계산', '입력값을 바탕으로 중간 결과를 계산하는 영역'),
  total: present('result', '합계·소계', '데이터를 집계한 결과 영역'),
  output: present('result', '출력', '판단에 직접 사용하는 최종 결과 영역'),
  note: present('meta', '주석', '참고 또는 보충 설명을 제공하는 영역'),
  instruction: present('meta', '안내', '워크북 사용 방법을 설명하는 영역'),
  source_note: present('meta', '출처', '데이터 출처와 기준일을 설명하는 영역'),
  rule_note: present('meta', '판단 기준', '결과를 해석하는 조건과 기준을 설명하는 영역'),
  warning: present('caution', '주의', '사용자가 확인해야 할 주의·경고 영역'),
  system_cache: present('meta', '시스템', '업무 분석에서 제외되는 시스템 데이터 영역'),
  ignore: present('meta', '제외', '분석에 사용하지 않는 영역'),
  unknown: present('meta', '미분류', '현재 규칙으로 역할을 확정하지 못한 영역'),
}
