import { ShieldCheck } from 'lucide-react'

import type { ManagedUser } from '@/api/auth'

export const UserIdentity = ({ user }: { user: ManagedUser }) => (
  <div className="flex min-w-0 items-center gap-3">
    <span className="grid size-9 shrink-0 place-items-center rounded-xl bg-brand-50 text-xs font-extrabold text-brand-700">
      {user.displayName.slice(0, 1).toUpperCase()}
    </span>
    <div className="min-w-0">
      <p className="truncate font-bold text-slate-900">{user.displayName}</p>
      <p className="mt-0.5 truncate text-xs text-slate-400">
        {user.email ?? user.username}
      </p>
    </div>
  </div>
)

export const RoleBadge = ({ user }: { user: ManagedUser }) => (
  <span className="inline-flex items-center gap-1.5 rounded-full bg-slate-100 px-2.5 py-1 text-xs font-bold text-slate-600">
    <ShieldCheck aria-hidden="true" size={13} />
    {user.role === 'ADMIN' ? '관리자' : '사용자'}
  </span>
)
