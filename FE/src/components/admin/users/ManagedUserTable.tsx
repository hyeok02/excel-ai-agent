import { LoaderCircle, UsersRound } from 'lucide-react'
import { useState } from 'react'

import type { ManagedUser } from '@/api/auth'
import { RoleBadge, UserIdentity } from '@/components/admin/users/ManagedUserPresentation'
import ManagedUserStatusControl from '@/components/admin/users/ManagedUserStatusControl'
import { MANAGED_USER_DATE_FORMATTER } from '@/components/admin/users/userDateFormatter'

interface ManagedUserTableProps {
  currentUserId: string | null
  isLoading: boolean
  isUpdatePending: boolean
  onStatusChange: (user: ManagedUser, enabled: boolean) => Promise<void>
  updatingUserId: string | null
  users: ManagedUser[]
}

const ManagedUserTable = ({
  currentUserId,
  isLoading,
  isUpdatePending,
  onStatusChange,
  updatingUserId,
  users,
}: ManagedUserTableProps) => {
  const [confirmingId, setConfirmingId] = useState<string | null>(null)

  const requestStatusChange = (user: ManagedUser) => {
    if (user.enabled) {
      setConfirmingId(user.id)
      return
    }
    void onStatusChange(user, true)
  }
  const confirmDisable = (user: ManagedUser) => {
    setConfirmingId(null)
    void onStatusChange(user, false)
  }
  const statusControl = (user: ManagedUser) => (
    <ManagedUserStatusControl
      currentUserId={currentUserId}
      isConfirming={confirmingId === user.id}
      isUpdatePending={isUpdatePending}
      onCancel={() => setConfirmingId(null)}
      onConfirmDisable={() => confirmDisable(user)}
      onRequestChange={() => requestStatusChange(user)}
      updatingUserId={updatingUserId}
      user={user}
    />
  )

  return (
    <section className="panel overflow-hidden">
      <div className="flex items-start justify-between gap-4 border-b border-slate-100 px-5 py-5 sm:px-6">
        <div>
          <h2 className="section-title">등록 사용자</h2>
          <p className="section-description">로컬 계정과 SSO 사용자를 함께 관리합니다.</p>
        </div>
        <span className="inline-flex shrink-0 items-center gap-1.5 rounded-full bg-brand-50 px-2.5 py-1 text-xs font-extrabold text-brand-700">
          <UsersRound aria-hidden="true" size={13} /> {users.length}명
        </span>
      </div>

      {isLoading ? (
        <div
          aria-live="polite"
          className="flex min-h-64 items-center justify-center gap-2 text-sm text-slate-500"
        >
          <LoaderCircle aria-hidden="true" className="animate-spin" size={18} /> 사용자
          목록을 불러오는 중
        </div>
      ) : users.length === 0 ? (
        <div className="grid min-h-52 place-items-center px-6 text-center text-sm text-slate-400">
          등록된 사용자가 없습니다.
        </div>
      ) : (
        <>
          <div className="divide-y divide-slate-100 md:hidden">
            {users.map((user) => (
              <article className="space-y-4 px-5 py-5" key={user.id}>
                <UserIdentity user={user} />
                <dl className="grid grid-cols-2 gap-x-4 gap-y-3 text-xs">
                  <div>
                    <dt className="font-bold text-slate-400">로그인 방식</dt>
                    <dd className="mt-1 text-slate-600">
                      {user.authProvider === 'SSO' ? '회사 SSO' : '사내 계정'}
                    </dd>
                  </div>
                  <div>
                    <dt className="font-bold text-slate-400">권한</dt>
                    <dd className="mt-1">
                      <RoleBadge user={user} />
                    </dd>
                  </div>
                  <div>
                    <dt className="font-bold text-slate-400">등록일</dt>
                    <dd className="mt-1 text-slate-600">
                      {MANAGED_USER_DATE_FORMATTER.format(new Date(user.createdAt))}
                    </dd>
                  </div>
                </dl>
                <div className="border-t border-slate-100 pt-3">
                  {statusControl(user)}
                </div>
              </article>
            ))}
          </div>

          <div className="hidden overflow-x-auto md:block">
            <table className="w-full min-w-[54rem] text-left">
              <thead className="bg-slate-50/80 text-[0.7rem] font-bold uppercase tracking-[0.08em] text-slate-400">
                <tr>
                  {['사용자', '로그인 방식', '권한', '상태 및 관리', '등록일'].map(
                    (label) => (
                      <th className="px-5 py-3.5 first:pl-6" key={label}>
                        {label}
                      </th>
                    ),
                  )}
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {users.map((user) => (
                  <tr className="text-sm text-slate-600" key={user.id}>
                    <td className="px-6 py-4">
                      <UserIdentity user={user} />
                    </td>
                    <td className="px-5 py-4">
                      {user.authProvider === 'SSO' ? '회사 SSO' : '사내 계정'}
                    </td>
                    <td className="px-5 py-4">
                      <RoleBadge user={user} />
                    </td>
                    <td className="px-5 py-4">{statusControl(user)}</td>
                    <td className="px-6 py-4 text-xs text-slate-400">
                      {MANAGED_USER_DATE_FORMATTER.format(new Date(user.createdAt))}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </>
      )}
    </section>
  )
}

export default ManagedUserTable
