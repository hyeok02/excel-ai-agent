import type { WritebackChange } from '@/api/analysis'

/** 셀 값을 화면에 보여줄 문자열로 바꾼다. 원본 서식대로 보이는 값이 있으면 그것을 쓴다. */
export const showValue = (
  value: WritebackChange['oldValue'],
  display?: string | null,
) => {
  if (display) return display
  if (value === null) return '(빈 셀)'
  if (typeof value === 'boolean') return value ? 'TRUE' : 'FALSE'
  return String(value)
}
