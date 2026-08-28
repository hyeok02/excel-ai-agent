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
}
