import { Check, LoaderCircle, Power, PowerOff, X } from 'lucide-react'

import type { ManagedUser } from '@/api/auth'

interface ManagedUserStatusControlProps {
  currentUserId: string | null
  isConfirming: boolean
  isUpdatePending: boolean
  onCancel: () => void
  onConfirmDisable: () => void
  onRequestChange: () => void
  updatingUserId: string | null
  user: ManagedUser
}

const ManagedUserStatusControl = ({
  currentUserId,
  isConfirming,
  isUpdatePending,
  onCancel,
  onConfirmDisable,
  onRequestChange,
  updatingUserId,
  user,
}: ManagedUserStatusControlProps) => {
  const isCurrentUser = user.id === currentUserId
  const isUpdating = updatingUserId === user.id
  const actionLabel = user.enabled ? '비활성화' : '활성화'

  return (
    <div className="flex flex-wrap items-center gap-2" aria-live="polite">
      <span
        className={`inline-flex items-center gap-1.5 text-xs font-bold ${
          user.enabled ? 'text-emerald-600' : 'text-slate-400'
        }`}
      >
        <span
          className={`size-1.5 rounded-full ${
            user.enabled ? 'bg-emerald-500' : 'bg-slate-300'
          }`}
        />
        {user.enabled ? '활성' : '비활성'}
      </span>

      {isCurrentUser ? (
        <span className="max-w-44 text-[0.68rem] font-medium leading-4 text-slate-400">
          현재 로그인 계정은 변경할 수 없습니다
        </span>
      ) : isConfirming ? (
        <div className="flex items-center gap-1.5">
          <button
            aria-label={`${user.displayName} 비활성화 취소`}
            className="inline-flex h-8 items-center gap-1 rounded-lg border border-transparent px-2 text-[0.7rem] font-bold text-slate-500 transition hover:border-slate-200 hover:bg-white hover:text-slate-700 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-slate-300 focus-visible:ring-offset-1 disabled:cursor-wait disabled:opacity-50"
            disabled={isUpdatePending}
            onClick={onCancel}
            type="button"
          >
            <X aria-hidden="true" size={12} /> 취소
          </button>
          <button
            aria-label={`${user.displayName} 계정 비활성화 확인`}
            className="inline-flex h-8 items-center gap-1 rounded-lg border border-red-200 bg-red-50 px-2.5 text-[0.7rem] font-extrabold text-red-800 shadow-sm transition hover:border-red-300 hover:bg-red-100 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-red-300 focus-visible:ring-offset-1 disabled:cursor-wait disabled:opacity-50"
            disabled={isUpdatePending}
            onClick={onConfirmDisable}
            type="button"
          >
            <Check aria-hidden="true" size={12} /> 비활성화 확인
          </button>
        </div>
      ) : (
        <button
          aria-label={`${user.displayName} 계정 ${actionLabel}`}
          className={`inline-flex h-8 items-center gap-1 rounded-lg border bg-white px-2.5 text-[0.7rem] font-bold transition disabled:cursor-wait disabled:opacity-50 ${
            user.enabled
              ? 'border-slate-200 text-slate-500 hover:border-red-200 hover:bg-red-50 hover:text-red-600'
              : 'border-emerald-200 text-emerald-700 hover:bg-emerald-50'
          }`}
          disabled={isUpdatePending}
          onClick={onRequestChange}
          type="button"
        >
          {isUpdating ? (
            <LoaderCircle aria-hidden="true" className="animate-spin" size={12} />
          ) : user.enabled ? (
            <PowerOff aria-hidden="true" size={12} />
          ) : (
            <Power aria-hidden="true" size={12} />
          )}
          {isUpdating ? '변경 중…' : actionLabel}
        </button>
      )}
    </div>
  )
}

export default ManagedUserStatusControl
