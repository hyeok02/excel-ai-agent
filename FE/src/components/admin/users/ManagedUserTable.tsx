import { LoaderCircle, ShieldCheck } from 'lucide-react'

import type { ManagedUser } from '@/api/auth'

interface ManagedUserTableProps {
  isLoading: boolean
  users: ManagedUser[]
}

const DATE_FORMATTER = new Intl.DateTimeFormat('ko-KR', { dateStyle: 'medium' })

const ManagedUserTable = ({ isLoading, users }: ManagedUserTableProps) => (
  <section className="panel overflow-hidden">
    <div className="border-b border-slate-100 px-6 py-5">
      <h2 className="section-title">등록 사용자</h2>
      <p className="section-description">로컬 계정과 SSO 사용자를 함께 확인합니다.</p>
    </div>

    {isLoading ? (
      <div className="flex min-h-64 items-center justify-center gap-2 text-sm text-slate-500">
        <LoaderCircle className="animate-spin" size={18} /> 사용자 목록을 불러오는 중
      </div>
    ) : (
      <div className="overflow-x-auto">
        <table className="w-full min-w-[42rem] text-left">
          <thead className="bg-slate-50/80 text-[0.7rem] font-bold uppercase tracking-[0.08em] text-slate-400">
            <tr>
              <th className="px-6 py-3.5">사용자</th>
              <th className="px-5 py-3.5">로그인 방식</th>
              <th className="px-5 py-3.5">권한</th>
              <th className="px-5 py-3.5">상태</th>
              <th className="px-6 py-3.5">등록일</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100">
            {users.map((user) => (
              <tr className="text-sm text-slate-600" key={user.id}>
                <td className="px-6 py-4">
                  <div className="flex items-center gap-3">
                    <span className="grid size-9 place-items-center rounded-xl bg-brand-50 text-xs font-extrabold text-brand-700">
                      {user.displayName.slice(0, 1).toUpperCase()}
                    </span>
                    <div>
                      <p className="font-bold text-slate-900">{user.displayName}</p>
                      <p className="mt-0.5 text-xs text-slate-400">
                        {user.email ?? user.username}
                      </p>
                    </div>
                  </div>
                </td>
                <td className="px-5 py-4">
                  {user.authProvider === 'SSO' ? '회사 SSO' : '사내 계정'}
                </td>
                <td className="px-5 py-4">
                  <span className="inline-flex items-center gap-1.5 rounded-full bg-slate-100 px-2.5 py-1 text-xs font-bold text-slate-600">
                    <ShieldCheck size={13} />{' '}
                    {user.role === 'ADMIN' ? '관리자' : '사용자'}
                  </span>
                </td>
                <td className="px-5 py-4">
                  <span className="inline-flex items-center gap-1.5 text-xs font-bold text-emerald-600">
                    <span className="size-1.5 rounded-full bg-emerald-500" />
                    {user.enabled ? '활성' : '비활성'}
                  </span>
                </td>
                <td className="px-6 py-4 text-xs text-slate-400">
                  {DATE_FORMATTER.format(new Date(user.createdAt))}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    )}
  </section>
)

export default ManagedUserTable
