import { CheckCircle2, CircleAlert } from 'lucide-react'
import { useEffect, useState } from 'react'

interface UserStatusNoticeProps {
  notice: {
    id: number
    kind: 'error' | 'success'
    message: string
  }
  onDismiss: (noticeId: number) => void
}

const EXIT_START_MS = 5_000
const REMOVE_AFTER_MS = 5_500

const UserStatusNotice = ({ notice, onDismiss }: UserStatusNoticeProps) => {
  const [isLeaving, setIsLeaving] = useState(false)
  const isError = notice.kind === 'error'
  const Icon = isError ? CircleAlert : CheckCircle2

  useEffect(() => {
    const prefersReducedMotion = window.matchMedia(
      '(prefers-reduced-motion: reduce)',
    ).matches
    const exitTimer = window.setTimeout(() => {
      if (!prefersReducedMotion) setIsLeaving(true)
    }, EXIT_START_MS)
    const removalTimer = window.setTimeout(() => onDismiss(notice.id), REMOVE_AFTER_MS)

    return () => {
      window.clearTimeout(exitTimer)
      window.clearTimeout(removalTimer)
    }
  }, [notice.id, onDismiss])

  return (
    <div
      aria-atomic="true"
      className={`flex transform-gpu items-start gap-3 rounded-2xl border px-4 py-3 text-sm shadow-sm transition-[opacity,transform] duration-500 ease-in motion-reduce:transform-none motion-reduce:transition-none ${
        isLeaving ? 'translate-y-3 opacity-0' : 'translate-y-0 opacity-100'
      } ${
        isError
          ? 'border-red-200 bg-red-50 text-red-800'
          : 'border-emerald-200 bg-emerald-50 text-emerald-800'
      }`}
      role={isError ? 'alert' : 'status'}
    >
      <Icon aria-hidden="true" className="mt-0.5 shrink-0" size={16} />
      <div>
        <p className="font-bold">
          {isError ? '계정 상태를 변경하지 못했습니다.' : notice.message}
        </p>
        {isError && <p className="mt-1 text-xs text-red-700">{notice.message}</p>}
      </div>
    </div>
  )
}

export default UserStatusNotice
