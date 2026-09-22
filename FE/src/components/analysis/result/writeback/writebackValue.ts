import type { WritebackChange } from '@/api/analysis'

/** 셀 값을 화면에 보여줄 문자열로 바꾼다. */
export const showValue = (value: WritebackChange['oldValue']) => {
  if (value === null) return '(빈 셀)'
  if (typeof value === 'boolean') return value ? 'TRUE' : 'FALSE'
  return String(value)
}
