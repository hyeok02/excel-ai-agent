import type { FormulaRiskKind } from '@/api/analysis'

export const FORMULA_RISK_PRESENTATION: Record<
  FormulaRiskKind,
  { label: string; action: string }
> = {
  broken_reference: {
    label: '깨진 셀 참조',
    action: '삭제되거나 이동된 셀을 다시 연결해야 합니다.',
  },
  missing_sheet: {
    label: '없는 시트 참조',
    action: '참조할 시트가 삭제 또는 변경됐는지 확인해야 합니다.',
  },
  external_reference: {
    label: '외부 파일 연결',
    action: '원본 파일의 위치와 접근 권한을 확인해야 합니다.',
  },
  dynamic_function: {
    label: '추적이 어려운 동적 참조',
    action: 'INDIRECT·OFFSET이 실제로 가리키는 범위를 확인해야 합니다.',
  },
  formula_pattern_mismatch: {
    label: '반복 수식 패턴 이상',
    action: '같은 행·열의 주변 수식과 달라 복사 또는 수정 과정의 오류인지 확인해야 합니다.',
  },
  hardcoded_value: {
    label: '수식 대신 직접 입력된 값',
    action: '반복 계산 구간에 값이 직접 입력되어 최신 데이터 반영이 누락될 수 있습니다.',
  },
}

export const FORMULA_RISK_LEVEL_PRESENTATION = {
  critical: { label: '즉시 확인', className: 'bg-red-100 text-red-700' },
  high: { label: '우선 확인', className: 'bg-orange-100 text-orange-700' },
  medium: { label: '확인 필요', className: 'bg-amber-100 text-amber-700' },
  low: { label: '낮은 위험', className: 'bg-slate-100 text-slate-600' },
} as const
