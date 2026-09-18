import type { TelegramInvitation, TelegramRecipient } from '@/api/telegram'

const DATE_FORMATTER = new Intl.DateTimeFormat('ko-KR', {
  dateStyle: 'medium',
  timeStyle: 'short',
})

export const formatTelegramDate = (value: string) =>
  DATE_FORMATTER.format(new Date(value))

export const getRecipientStatus = (status: TelegramRecipient['status']) =>
  status === 'ACTIVE'
    ? {
        label: '수신 가능',
        badgeClass: 'bg-emerald-50 text-emerald-700',
        dotClass: 'bg-emerald-500',
      }
    : {
        label: '연결 확인 필요',
        badgeClass: 'bg-amber-50 text-amber-700',
        dotClass: 'bg-amber-500',
      }

export const getInvitationStatus = (status: TelegramInvitation['status']) => {
  if (status === 'ACTIVE') {
    return { label: '등록 대기', className: 'bg-amber-50 text-amber-700' }
  }
  if (status === 'CONSUMED') {
    return { label: '등록 완료', className: 'bg-emerald-50 text-emerald-700' }
  }
  if (status === 'EXPIRED') {
    return { label: '기간 만료', className: 'bg-slate-100 text-slate-500' }
  }
  return { label: '초대 취소', className: 'bg-slate-100 text-slate-500' }
}
