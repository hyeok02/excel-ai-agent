import type { WritebackStatus } from '@/api/analysis'

export const WRITEBACK_STATUS_PRESENTATION: Record<
  WritebackStatus,
  { label: string; style: string }
> = {
  PROPOSED: { label: '승인 대기', style: 'bg-amber-100 text-amber-700' },
  BLOCKED: { label: '안전 기준으로 차단', style: 'bg-red-50 text-red-700' },
  APPLIED: { label: '적용·검증 완료', style: 'bg-emerald-100 text-emerald-700' },
  REJECTED: { label: '사용자 거절', style: 'bg-slate-200 text-slate-600' },
  FAILED: { label: '수정·검증 실패', style: 'bg-red-100 text-red-700' },
}
